"""
Integração Stripe simplificada e funcional
"""
import os
import stripe
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from models import User, Product, License, Transaction

# Configurar Stripe
stripe.api_key = os.environ.get('STRIPE_SECRET_KEY')

def create_stripe_checkout_session(user_id: int, product_id: int, db: Session) -> dict:
    """Criar sessão de checkout do Stripe"""
    try:
        # Buscar produto e usuário
        product = db.query(Product).filter(Product.id == product_id).first()
        user = db.query(User).filter(User.id == user_id).first()
        
        if not product or not user:
            return {"success": False, "error": "Produto ou usuário não encontrado"}
        
        # URL base
        base_url = os.environ.get('REPLIT_DEV_DOMAIN', 'localhost:5000')
        if not base_url.startswith('http'):
            base_url = f"https://{base_url}"
        
        # Criar sessão
        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': 'brl',
                    'product_data': {
                        'name': str(product.name),
                        'description': f"Licença de {product.duration_days} dias",
                    },
                    'unit_amount': int(float(product.price) * 100),
                },
                'quantity': 1,
            }],
            mode='payment',
            success_url=f"{base_url}/payment/success?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{base_url}/payment/cancel",
            metadata={
                'user_id': str(user_id),
                'product_id': str(product_id),
                'duration_days': str(product.duration_days),
            },
            customer_email=str(user.email),
            expires_at=int((datetime.utcnow() + timedelta(minutes=30)).timestamp()),
        )
        
        # Salvar transação pendente
        transaction = Transaction(
            user_id=user_id,
            product_id=product_id,
            amount=float(product.price),
            payment_id=session.id,
            payment_method='stripe',
            status='pending'
        )
        db.add(transaction)
        db.commit()
        
        return {
            'success': True,
            'checkout_url': session.url,
            'session_id': session.id,
            'amount': float(product.price),
            'product_name': str(product.name),
            'duration_days': product.duration_days
        }
        
    except Exception as e:
        print(f"Erro ao criar checkout Stripe: {e}")
        return {'success': False, 'error': str(e)}

def process_stripe_webhook_event(payload: bytes, signature: str, db: Session) -> dict:
    """Processar webhook do Stripe"""
    try:
        import json
        
        # Em desenvolvimento, processar sem verificação de assinatura
        # Em produção, adicionar verificação com STRIPE_WEBHOOK_SECRET
        event = json.loads(payload.decode('utf-8'))
        
        if event['type'] == 'checkout.session.completed':
            return handle_payment_success(event['data']['object'], db)
        elif event['type'] == 'checkout.session.expired':
            return handle_payment_expired(event['data']['object'], db)
        
        return {'success': True, 'message': 'Evento processado'}
        
    except Exception as e:
        print(f"Erro no webhook: {e}")
        return {'success': False, 'error': str(e)}

def handle_payment_success(session_data: dict, db: Session) -> dict:
    """Processar pagamento bem-sucedido"""
    try:
        session_id = session_data['id']
        metadata = session_data.get('metadata', {})
        
        user_id = int(metadata.get('user_id'))
        product_id = int(metadata.get('product_id'))
        duration_days = int(metadata.get('duration_days', 30))
        
        # Atualizar transação
        transaction = db.query(Transaction).filter(
            Transaction.payment_id == session_id
        ).first()
        
        if transaction:
            # Usar update() para evitar problemas de tipo
            db.query(Transaction).filter(
                Transaction.payment_id == session_id
            ).update({
                'status': 'approved',
                'updated_at': datetime.utcnow()
            })
        
        # Verificar licença existente
        existing_license = db.query(License).filter(
            License.user_id == user_id,
            License.product_id == product_id,
            License.status == 'active'
        ).first()
        
        if existing_license:
            # Estender licença existente
            new_expiry = existing_license.expires_at + timedelta(days=duration_days)
            db.query(License).filter(
                License.id == existing_license.id
            ).update({
                'expires_at': new_expiry,
                'stripe_session_id': session_id
            })
            license_key = existing_license.license_key
        else:
            # Criar nova licença
            license = License(
                user_id=user_id,
                product_id=product_id,
                status='active',
                expires_at=datetime.utcnow() + timedelta(days=duration_days),
                stripe_session_id=session_id
            )
            db.add(license)
            db.flush()  # Para obter o license_key gerado
            license_key = license.license_key
        
        # Incrementar contador de downloads
        db.query(Product).filter(
            Product.id == product_id
        ).update({
            'download_count': Product.download_count + 1
        })
        
        db.commit()
        
        return {
            'success': True,
            'message': 'Licença criada com sucesso',
            'license_key': license_key
        }
        
    except Exception as e:
        print(f"Erro ao processar pagamento: {e}")
        db.rollback()
        return {'success': False, 'error': str(e)}

def handle_payment_expired(session_data: dict, db: Session) -> dict:
    """Processar pagamento expirado"""
    try:
        session_id = session_data['id']
        
        db.query(Transaction).filter(
            Transaction.payment_id == session_id
        ).update({
            'status': 'expired',
            'updated_at': datetime.utcnow()
        })
        
        db.commit()
        return {'success': True, 'message': 'Pagamento expirado'}
        
    except Exception as e:
        print(f"Erro ao processar expiração: {e}")
        return {'success': False, 'error': str(e)}

def check_user_license(db: Session, user_id: int, product_id: int) -> dict:
    """Verificar se usuário tem licença ativa"""
    try:
        license = db.query(License).filter(
            License.user_id == user_id,
            License.product_id == product_id,
            License.status == 'active',
            License.expires_at > datetime.utcnow()
        ).first()
        
        if license:
            return {
                'has_license': True,
                'license_key': license.license_key,
                'expires_at': license.expires_at.isoformat(),
                'days_remaining': (license.expires_at - datetime.utcnow()).days
            }
        else:
            return {'has_license': False}
            
    except Exception as e:
        print(f"Erro ao verificar licença: {e}")
        return {'has_license': False, 'error': str(e)}

def get_user_active_licenses(db: Session, user_id: int) -> list:
    """Obter licenças ativas do usuário"""
    try:
        licenses = db.query(License).join(Product).filter(
            License.user_id == user_id,
            License.status == 'active',
            License.expires_at > datetime.utcnow()
        ).all()
        
        result = []
        for license in licenses:
            result.append({
                'license_key': license.license_key,
                'product_name': license.product.name,
                'product_id': license.product_id,
                'expires_at': license.expires_at.isoformat(),
                'days_remaining': (license.expires_at - datetime.utcnow()).days,
                'download_url': license.product.download_url
            })
        
        return result
        
    except Exception as e:
        print(f"Erro ao obter licenças: {e}")
        return []