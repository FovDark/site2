"""
Integração completa com Stripe para processamento de pagamentos
Sistema de licenças baseado em dias e controle de downloads
"""
import os
import stripe
import hashlib
import hmac
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from models import User, Product, License, Transaction
from database import get_db
from config import Config

# Configurar Stripe
stripe.api_key = os.environ.get('STRIPE_SECRET_KEY')

class StripeManager:
    """Gerenciador de pagamentos Stripe"""
    
    def __init__(self):
        self.api_key = os.environ.get('STRIPE_SECRET_KEY')
        if not self.api_key:
            raise ValueError("STRIPE_SECRET_KEY não configurada")
        stripe.api_key = self.api_key
        
        # URL base do ambiente Replit
        replit_domain = os.environ.get('REPLIT_DEV_DOMAIN')
        if replit_domain:
            self.base_url = f"https://{replit_domain}"
        else:
            # Fallback para desenvolvimento local
            self.base_url = "http://localhost:5000"
    
    def create_checkout_session(self, user_id: int, product_id: int, db: Session) -> dict:
        """Criar sessão de checkout do Stripe"""
        try:
            # Buscar produto
            product = db.query(Product).filter(Product.id == product_id).first()
            if not product:
                raise ValueError("Produto não encontrado")
            
            # Buscar usuário
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                raise ValueError("Usuário não encontrado")
            
            # Calcular preço em centavos (Stripe usa centavos)
            price_cents = int(float(product.price) * 100)
            
            # Criar sessão de checkout
            session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=[{
                    'price_data': {
                        'currency': 'brl',
                        'product_data': {
                            'name': product.name,
                            'description': f"Licença de {product.duration_days} dias para {product.name}",
                            'images': [product.image_url] if product.image_url else [],
                        },
                        'unit_amount': price_cents,
                    },
                    'quantity': 1,
                }],
                mode='payment',
                success_url=f"{self.base_url}/payment/success?session_id={{CHECKOUT_SESSION_ID}}",
                cancel_url=f"{self.base_url}/payment/cancel",
                metadata={
                    'user_id': str(user_id),
                    'product_id': str(product_id),
                    'duration_days': str(product.duration_days),
                    'product_name': product.name,
                },
                customer_email=user.email,
                expires_at=int((datetime.utcnow() + timedelta(minutes=30)).timestamp()),
            )
            
            # Salvar transação pendente
            transaction = Transaction(
                user_id=user_id,
                product_id=product_id,
                amount=product.price,
                payment_id=session.id,
                payment_method='stripe',
                status='pending',
                gateway_response={'stripe_session': session.to_dict()}
            )
            db.add(transaction)
            db.commit()
            
            return {
                'success': True,
                'checkout_url': session.url,
                'session_id': session.id,
                'amount': product.price,
                'product_name': product.name,
                'duration_days': product.duration_days
            }
            
        except Exception as e:
            print(f"Erro ao criar sessão Stripe: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def process_webhook(self, payload: bytes, signature: str, db: Session) -> dict:
        """Processar webhook do Stripe"""
        try:
            # Verificar assinatura do webhook
            endpoint_secret = os.environ.get('STRIPE_WEBHOOK_SECRET')
            if endpoint_secret:
                try:
                    event = stripe.Webhook.construct_event(
                        payload, signature, endpoint_secret
                    )
                except stripe.error.SignatureVerificationError:
                    return {'success': False, 'error': 'Assinatura inválida'}
            else:
                # Em desenvolvimento, processar sem verificação
                import json
                event = json.loads(payload.decode('utf-8'))
            
            # Processar evento
            if event['type'] == 'checkout.session.completed':
                return self._handle_successful_payment(event['data']['object'], db)
            elif event['type'] == 'checkout.session.expired':
                return self._handle_expired_payment(event['data']['object'], db)
            
            return {'success': True, 'message': 'Evento processado'}
            
        except Exception as e:
            print(f"Erro ao processar webhook: {e}")
            return {'success': False, 'error': str(e)}
    
    def _handle_successful_payment(self, session_data: dict, db: Session) -> dict:
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
                transaction.status = 'approved'
                transaction.updated_at = datetime.utcnow()
                transaction.gateway_response = {
                    **transaction.gateway_response,
                    'payment_completed': session_data
                }
            
            # Verificar se já existe licença ativa para este produto
            existing_license = db.query(License).filter(
                License.user_id == user_id,
                License.product_id == product_id,
                License.status == 'active'
            ).first()
            
            if existing_license:
                # Estender licença existente
                existing_license.expires_at = existing_license.expires_at + timedelta(days=duration_days)
                existing_license.payment_amount = session_data.get('amount_total', 0) / 100
                existing_license.stripe_session_id = session_id
                license = existing_license
            else:
                # Criar nova licença
                license = License(
                    user_id=user_id,
                    product_id=product_id,
                    status='active',
                    expires_at=datetime.utcnow() + timedelta(days=duration_days),
                    payment_amount=session_data.get('amount_total', 0) / 100,
                    payment_currency='BRL',
                    stripe_session_id=session_id
                )
                db.add(license)
            
            # Atualizar contador de downloads do produto
            product = db.query(Product).filter(Product.id == product_id).first()
            if product:
                product.download_count += 1
            
            db.commit()
            
            return {
                'success': True,
                'message': 'Licença criada/estendida com sucesso',
                'license_key': license.license_key,
                'expires_at': license.expires_at.isoformat(),
                'days_remaining': license.days_remaining
            }
            
        except Exception as e:
            print(f"Erro ao processar pagamento: {e}")
            db.rollback()
            return {'success': False, 'error': str(e)}
    
    def _handle_expired_payment(self, session_data: dict, db: Session) -> dict:
        """Processar pagamento expirado"""
        try:
            session_id = session_data['id']
            
            # Atualizar transação
            transaction = db.query(Transaction).filter(
                Transaction.payment_id == session_id
            ).first()
            
            if transaction:
                transaction.status = 'expired'
                transaction.updated_at = datetime.utcnow()
                db.commit()
            
            return {'success': True, 'message': 'Pagamento expirado processado'}
            
        except Exception as e:
            print(f"Erro ao processar expiração: {e}")
            return {'success': False, 'error': str(e)}
    
    def get_payment_status(self, session_id: str) -> dict:
        """Obter status do pagamento"""
        try:
            session = stripe.checkout.Session.retrieve(session_id)
            return {
                'success': True,
                'status': session.payment_status,
                'session': session.to_dict()
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}

def create_stripe_checkout(user_id: int, product_id: int, db: Session) -> dict:
    """Função wrapper para criar checkout"""
    manager = StripeManager()
    return manager.create_checkout_session(user_id, product_id, db)

def process_stripe_webhook(payload: bytes, signature: str, db: Session) -> dict:
    """Função wrapper para processar webhook"""
    manager = StripeManager()
    return manager.process_webhook(payload, signature, db)

def verify_user_license(db: Session, user_id: int, product_id: int) -> dict:
    """Verificar se usuário tem licença ativa para o produto"""
    try:
        license = db.query(License).filter(
            License.user_id == user_id,
            License.product_id == product_id,
            License.status == 'active'
        ).first()
        
        if not license:
            return {
                'has_license': False,
                'message': 'Licença não encontrada'
            }
        
        if license.is_expired:
            # Atualizar status da licença expirada
            license.status = 'expired'
            db.commit()
            return {
                'has_license': False,
                'message': 'Licença expirada'
            }
        
        return {
            'has_license': True,
            'license_key': license.license_key,
            'expires_at': license.expires_at.isoformat(),
            'days_remaining': license.days_remaining,
            'time_remaining': license.time_remaining,
            'formatted_time': license.formatted_time_remaining
        }
        
    except Exception as e:
        print(f"Erro ao verificar licença: {e}")
        return {
            'has_license': False,
            'message': f'Erro interno: {str(e)}'
        }

def get_user_licenses(db: Session, user_id: int) -> list:
    """Obter todas as licenças do usuário"""
    try:
        licenses = db.query(License).filter(
            License.user_id == user_id
        ).join(Product).all()
        
        result = []
        for license in licenses:
            result.append({
                'license_key': license.license_key,
                'product_name': license.product.name,
                'product_id': license.product_id,
                'status': license.status,
                'expires_at': license.expires_at.isoformat(),
                'days_remaining': license.days_remaining,
                'time_remaining': license.formatted_time_remaining,
                'is_expired': license.is_expired,
                'can_download': license.status == 'active' and not license.is_expired
            })
        
        return result
        
    except Exception as e:
        print(f"Erro ao obter licenças: {e}")
        return []

def cleanup_expired_licenses(db: Session) -> int:
    """Limpar licenças expiradas (task de background)"""
    try:
        expired_count = db.query(License).filter(
            License.status == 'active',
            License.expires_at < datetime.utcnow()
        ).update({'status': 'expired'})
        
        db.commit()
        return expired_count
        
    except Exception as e:
        print(f"Erro ao limpar licenças: {e}")
        return 0

def test_stripe_connection() -> bool:
    """Testar conexão com Stripe"""
    try:
        stripe.api_key = os.environ.get('STRIPE_SECRET_KEY')
        stripe.Account.retrieve()
        return True
    except Exception as e:
        print(f"Erro de conexão Stripe: {e}")
        return False