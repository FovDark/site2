"""
Sincronização automática de produtos com Stripe
"""
import os
import stripe
import logging
from sqlalchemy.orm import Session
from models import Product
from config import get_config

logger = logging.getLogger(__name__)

# Configurar Stripe
stripe.api_key = os.environ.get('STRIPE_SECRET_KEY')

class StripeProductManager:
    """Gerenciador de sincronização de produtos com Stripe"""
    
    def __init__(self):
        self.config = get_config()
    
    def create_stripe_product(self, product: Product, db: Session) -> dict:
        """Criar produto no Stripe quando criado localmente"""
        try:
            # Criar produto no Stripe
            stripe_product = stripe.Product.create(
                name=product.name,
                description=product.description,
                metadata={
                    'local_product_id': str(product.id),
                    'category': product.category.name if product.category else 'Gaming',
                    'duration_days': str(product.duration_days),
                    'platform': 'FovDark Gaming'
                },
                images=[product.image_url] if product.image_url else [],
                active=product.is_active
            )
            
            # Criar preço no Stripe (em centavos)
            price_in_cents = int(float(product.price) * 100)
            stripe_price = stripe.Price.create(
                product=stripe_product.id,
                unit_amount=price_in_cents,
                currency='brl',
                metadata={
                    'local_product_id': str(product.id),
                    'duration_days': str(product.duration_days)
                }
            )
            
            # Atualizar produto local com IDs do Stripe
            product.stripe_product_id = stripe_product.id
            product.stripe_price_id = stripe_price.id
            db.commit()
            
            logger.info(f"Produto '{product.name}' criado no Stripe: {stripe_product.id}")
            
            return {
                'success': True,
                'stripe_product_id': stripe_product.id,
                'stripe_price_id': stripe_price.id,
                'message': f'Produto sincronizado com Stripe'
            }
            
        except Exception as e:
            logger.error(f"Erro ao criar produto no Stripe: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def update_stripe_product(self, product: Product, db: Session) -> dict:
        """Atualizar produto no Stripe quando editado localmente"""
        try:
            if not product.stripe_product_id:
                # Se não tem ID do Stripe, criar novo
                return self.create_stripe_product(product, db)
            
            # Atualizar produto no Stripe
            stripe.Product.modify(
                product.stripe_product_id,
                name=product.name,
                description=product.description,
                metadata={
                    'local_product_id': str(product.id),
                    'category': product.category.name if product.category else 'Gaming',
                    'duration_days': str(product.duration_days),
                    'platform': 'FovDark Gaming'
                },
                images=[product.image_url] if product.image_url else [],
                active=product.is_active
            )
            
            # Verificar se o preço mudou
            current_price_in_cents = int(float(product.price) * 100)
            
            if product.stripe_price_id:
                try:
                    current_stripe_price = stripe.Price.retrieve(product.stripe_price_id)
                    if current_stripe_price.unit_amount != current_price_in_cents:
                        # Preço mudou, criar novo preço (Stripe não permite editar preços)
                        # Arquivar preço antigo
                        stripe.Price.modify(product.stripe_price_id, active=False)
                        
                        # Criar novo preço
                        new_stripe_price = stripe.Price.create(
                            product=product.stripe_product_id,
                            unit_amount=current_price_in_cents,
                            currency='brl',
                            metadata={
                                'local_product_id': str(product.id),
                                'duration_days': str(product.duration_days)
                            }
                        )
                        
                        # Atualizar produto local com novo price_id
                        product.stripe_price_id = new_stripe_price.id
                        db.commit()
                        
                        logger.info(f"Novo preço criado para produto '{product.name}': {new_stripe_price.id}")
                        
                except stripe.error.InvalidRequestError:
                    # Preço não existe, criar novo
                    new_stripe_price = stripe.Price.create(
                        product=product.stripe_product_id,
                        unit_amount=current_price_in_cents,
                        currency='brl',
                        metadata={
                            'local_product_id': str(product.id),
                            'duration_days': str(product.duration_days)
                        }
                    )
                    product.stripe_price_id = new_stripe_price.id
                    db.commit()
            
            logger.info(f"Produto '{product.name}' atualizado no Stripe")
            
            return {
                'success': True,
                'stripe_product_id': product.stripe_product_id,
                'stripe_price_id': product.stripe_price_id,
                'message': 'Produto atualizado no Stripe'
            }
            
        except Exception as e:
            logger.error(f"Erro ao atualizar produto no Stripe: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def delete_stripe_product(self, product: Product, db: Session) -> dict:
        """Arquivar produto no Stripe quando deletado localmente"""
        try:
            if product.stripe_product_id:
                # Arquivar produto no Stripe (não pode ser deletado se tem vendas)
                stripe.Product.modify(
                    product.stripe_product_id,
                    active=False
                )
                
                # Arquivar preço associado
                if product.stripe_price_id:
                    stripe.Price.modify(
                        product.stripe_price_id,
                        active=False
                    )
                
                logger.info(f"Produto '{product.name}' arquivado no Stripe")
            
            return {
                'success': True,
                'message': 'Produto arquivado no Stripe'
            }
            
        except Exception as e:
            logger.error(f"Erro ao arquivar produto no Stripe: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def sync_all_products(self, db: Session) -> dict:
        """Sincronizar todos os produtos locais com Stripe"""
        try:
            products = db.query(Product).filter(Product.is_active == True).all()
            synced_count = 0
            errors = []
            
            for product in products:
                if not product.stripe_product_id:
                    result = self.create_stripe_product(product, db)
                    if result['success']:
                        synced_count += 1
                    else:
                        errors.append(f"Produto {product.name}: {result['error']}")
                else:
                    result = self.update_stripe_product(product, db)
                    if result['success']:
                        synced_count += 1
                    else:
                        errors.append(f"Produto {product.name}: {result['error']}")
            
            return {
                'success': True,
                'synced_count': synced_count,
                'total_products': len(products),
                'errors': errors
            }
            
        except Exception as e:
            logger.error(f"Erro na sincronização geral: {e}")
            return {
                'success': False,
                'error': str(e)
            }

def auto_sync_product_create(product: Product, db: Session) -> dict:
    """Função para ser chamada automaticamente na criação de produtos"""
    manager = StripeProductManager()
    return manager.create_stripe_product(product, db)

def auto_sync_product_update(product: Product, db: Session) -> dict:
    """Função para ser chamada automaticamente na atualização de produtos"""
    manager = StripeProductManager()
    return manager.update_stripe_product(product, db)

def auto_sync_product_delete(product: Product, db: Session) -> dict:
    """Função para ser chamada automaticamente na deleção de produtos"""
    manager = StripeProductManager()
    return manager.delete_stripe_product(product, db)

def validate_stripe_connection() -> bool:
    """Validar conexão com Stripe"""
    try:
        stripe.Account.retrieve()
        return True
    except Exception as e:
        logger.error(f"Erro na conexão com Stripe: {e}")
        return False