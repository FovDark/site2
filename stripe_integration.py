"""
Integração com Stripe para pagamentos FovDark Gaming
"""
import os
import stripe
from fastapi import HTTPException
from sqlalchemy.orm import Session
from models import Product, User, License
from license import create_license
from email_utils import send_license_email

# Configurar Stripe
stripe.api_key = os.getenv('STRIPE_SECRET_KEY')

def get_domain():
    """Obter domínio base para URLs de retorno"""
    if os.getenv('REPLIT_DEPLOYMENT'):
        return f"https://{os.getenv('REPLIT_DEV_DOMAIN')}"
    else:
        domains = os.getenv('REPLIT_DOMAINS', 'localhost:5000')
        return f"https://{domains.split(',')[0]}"

def create_checkout_session(product_id: int, user_id: int, db: Session) -> dict:
    """Criar sessão de checkout do Stripe"""
    try:
        # Buscar produto
        product = db.query(Product).filter(Product.id == product_id).first()
        if not product:
            raise HTTPException(status_code=404, detail="Produto não encontrado")
        
        # Buscar usuário
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="Usuário não encontrado")
        
        domain = get_domain()
        
        # Preparar dados do produto
        product_name = str(product.name)
        product_description = str(product.description)[:500] if product.description else ''
        product_price = float(product.price)
        user_email = str(user.email)
        duration_days = int(product.duration_days) if product.duration_days else 30
        
        # Criar sessão de checkout
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': 'brl',
                    'product_data': {
                        'name': product_name,
                        'description': product_description,
                    },
                    'unit_amount': int(product_price * 100),  # Stripe usa centavos
                },
                'quantity': 1,
            }],
            mode='payment',
            success_url=f'{domain}/payment/success?session_id={{CHECKOUT_SESSION_ID}}',
            cancel_url=f'{domain}/payment/cancel',
            client_reference_id=str(user_id),
            metadata={
                'product_id': str(product_id),
                'user_id': str(user_id),
                'duration_days': str(duration_days)
            },
            customer_email=user_email,
            billing_address_collection='auto',
        )
        
        return {
            'checkout_url': checkout_session.url,
            'session_id': checkout_session.id
        }
        
    except Exception as stripe_error:
        if hasattr(stripe_error, 'user_message'):
            raise HTTPException(status_code=400, detail=f"Erro no Stripe: {stripe_error.user_message}")
        else:
            raise HTTPException(status_code=400, detail=f"Erro no Stripe: {str(stripe_error)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")

def handle_successful_payment(session_id: str, db: Session) -> dict:
    """Processar pagamento bem-sucedido"""
    try:
        # Recuperar sessão do Stripe
        session = stripe.checkout.Session.retrieve(session_id)
        
        if session.payment_status != 'paid':
            raise HTTPException(status_code=400, detail="Pagamento não confirmado")
        
        # Extrair dados dos metadados
        metadata = session.metadata or {}
        user_id = int(metadata.get('user_id', 0))
        product_id = int(metadata.get('product_id', 0))
        duration_days = int(metadata.get('duration_days', 30))
        
        # Verificar se já existe licença para este pagamento
        existing_license = db.query(License).filter(
            License.stripe_session_id == session_id
        ).first()
        
        if existing_license:
            return {
                'license_key': existing_license.license_key,
                'message': 'Licença já foi criada para este pagamento'
            }
        
        # Buscar produto e usuário
        product = db.query(Product).filter(Product.id == product_id).first()
        user = db.query(User).filter(User.id == user_id).first()
        
        if not product or not user:
            raise HTTPException(status_code=404, detail="Produto ou usuário não encontrado")
        
        # Criar licença
        license_obj = create_license(
            db=db,
            user_id=user_id,
            product_id=product_id,
            duration_days=duration_days
        )
        
        # Atualizar licença com dados do Stripe
        db.execute(
            f"UPDATE licenses SET stripe_session_id = '{session_id}', "
            f"payment_amount = {session.amount_total / 100 if session.amount_total else 0}, "
            f"payment_currency = '{session.currency or 'BRL'}' "
            f"WHERE id = {license_obj.id}"
        )
        db.commit()
        
        # Enviar email com a licença
        try:
            user_email = str(user.email)
            send_license_email(user_email, license_obj, product)
        except Exception as e:
            print(f"Erro ao enviar email: {e}")
        
        return {
            'license_key': license_obj.license_key,
            'product_name': str(product.name),
            'expires_at': license_obj.expires_at.isoformat(),
            'message': 'Pagamento processado com sucesso!'
        }
        
    except Exception as stripe_error:
        if hasattr(stripe_error, 'user_message'):
            raise HTTPException(status_code=400, detail=f"Erro no Stripe: {stripe_error.user_message}")
        else:
            raise HTTPException(status_code=400, detail=f"Erro no Stripe: {str(stripe_error)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")

def verify_webhook_signature(payload: bytes, sig_header: str) -> dict:
    """Verificar assinatura do webhook do Stripe"""
    endpoint_secret = os.getenv('STRIPE_WEBHOOK_SECRET')
    
    if not endpoint_secret:
        raise HTTPException(status_code=500, detail="Webhook secret não configurado")
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, endpoint_secret
        )
        return event
    except ValueError:
        raise HTTPException(status_code=400, detail="Payload inválido")
    except Exception as e:
        raise HTTPException(status_code=400, detail="Assinatura inválida")

def process_webhook_event(event: dict, db: Session) -> dict:
    """Processar evento do webhook"""
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        return handle_successful_payment(session['id'], db)
    
    elif event['type'] == 'payment_intent.succeeded':
        # Pagamento confirmado
        return {'message': 'Pagamento confirmado'}
    
    elif event['type'] == 'payment_intent.payment_failed':
        # Pagamento falhou
        return {'message': 'Pagamento falhou'}
    
    else:
        return {'message': f'Evento não tratado: {event["type"]}'}

def get_payment_details(session_id: str) -> dict:
    """Obter detalhes do pagamento"""
    try:
        session = stripe.checkout.Session.retrieve(session_id)
        return {
            'session_id': session.id,
            'payment_status': session.payment_status,
            'amount_total': session.amount_total / 100 if session.amount_total else 0,
            'currency': session.currency,
            'customer_email': session.customer_email,
            'created': session.created
        }
    except Exception as stripe_error:
        if hasattr(stripe_error, 'user_message'):
            raise HTTPException(status_code=400, detail=f"Erro no Stripe: {stripe_error.user_message}")
        else:
            raise HTTPException(status_code=400, detail=f"Erro no Stripe: {str(stripe_error)}")

def create_product_in_stripe(product_name: str, price: float, description: str = None) -> str:
    """Criar produto no Stripe (opcional)"""
    try:
        stripe_product = stripe.Product.create(
            name=product_name,
            description=description[:500] if description else '',
        )
        
        stripe_price = stripe.Price.create(
            product=stripe_product.id,
            unit_amount=int(price * 100),
            currency='brl',
        )
        
        return stripe_price.id
    except Exception as stripe_error:
        if hasattr(stripe_error, 'user_message'):
            raise HTTPException(status_code=400, detail=f"Erro no Stripe: {stripe_error.user_message}")
        else:
            raise HTTPException(status_code=400, detail=f"Erro no Stripe: {str(stripe_error)}")

def test_stripe_connection() -> bool:
    """Testar conexão com Stripe"""
    try:
        stripe.Account.retrieve()
        return True
    except:
        return False