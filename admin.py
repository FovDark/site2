from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from models import User, Product, License, Transaction, Download, Category
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

def get_admin_stats(db: Session) -> dict:
    """Obter estatísticas para o painel administrativo"""
    try:
        # Estatísticas básicas
        total_users = db.query(User).count()
        active_users = db.query(User).filter(User.is_active == True).count()
        total_products = db.query(Product).count()
        active_products = db.query(Product).filter(Product.is_active == True).count()
        
        # Licenças
        total_licenses = db.query(License).count()
        active_licenses = db.query(License).filter(
            License.status == "active",
            License.expires_at > datetime.utcnow()
        ).count()
        expired_licenses = db.query(License).filter(
            License.expires_at <= datetime.utcnow()
        ).count()
        
        # Transações
        total_transactions = db.query(Transaction).count()
        approved_transactions = db.query(Transaction).filter(
            Transaction.status == "approved"
        ).count()
        pending_transactions = db.query(Transaction).filter(
            Transaction.status == "pending"
        ).count()
        
        # Receita total
        total_revenue = db.query(func.sum(Transaction.amount)).filter(
            Transaction.status == "approved"
        ).scalar() or 0
        
        # Receita do mês atual
        start_of_month = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        monthly_revenue = db.query(func.sum(Transaction.amount)).filter(
            Transaction.status == "approved",
            Transaction.created_at >= start_of_month
        ).scalar() or 0
        
        # Downloads
        total_downloads = db.query(Download).count()
        downloads_today = db.query(Download).filter(
            func.date(Download.downloaded_at) == datetime.utcnow().date()
        ).count()
        
        # Produtos mais populares
        popular_products = db.query(
            Product.name,
            func.count(Download.id).label('download_count')
        ).join(Download).group_by(Product.id, Product.name).order_by(
            desc('download_count')
        ).limit(5).all()
        
        # Registros recentes (últimos 7 dias)
        week_ago = datetime.utcnow() - timedelta(days=7)
        new_users_week = db.query(User).filter(
            User.created_at >= week_ago
        ).count()
        
        new_transactions_week = db.query(Transaction).filter(
            Transaction.created_at >= week_ago
        ).count()
        
        return {
            "users": {
                "total": total_users,
                "active": active_users,
                "new_this_week": new_users_week
            },
            "products": {
                "total": total_products,
                "active": active_products
            },
            "licenses": {
                "total": total_licenses,
                "active": active_licenses,
                "expired": expired_licenses
            },
            "transactions": {
                "total": total_transactions,
                "approved": approved_transactions,
                "pending": pending_transactions,
                "new_this_week": new_transactions_week
            },
            "revenue": {
                "total": total_revenue,
                "monthly": monthly_revenue
            },
            "downloads": {
                "total": total_downloads,
                "today": downloads_today
            },
            "popular_products": [
                {"name": name, "downloads": count} 
                for name, count in popular_products
            ]
        }
        
    except Exception as e:
        logger.error(f"Erro ao obter estatísticas: {e}")
        return {}

def create_product(db: Session, product_data: dict) -> Product:
    """Criar novo produto"""
    try:
        product = Product(
            name=product_data["name"],
            description=product_data["description"],
            price=product_data["price"],
            category_id=product_data["category_id"],
            duration_days=product_data.get("duration_days", 30),
            download_url=product_data.get("download_url"),
            requirements=product_data.get("requirements"),
            tags=product_data.get("tags"),
            image_url=product_data.get("image_url"),
            is_featured=product_data.get("is_featured", False)
        )
        
        db.add(product)
        db.commit()
        db.refresh(product)
        
        logger.info(f"Produto criado: {product.name}")
        return product
        
    except Exception as e:
        logger.error(f"Erro ao criar produto: {e}")
        db.rollback()
        raise

def update_product(db: Session, product_id: int, product_data: dict) -> Product:
    """Atualizar produto existente"""
    try:
        product = db.query(Product).filter(Product.id == product_id).first()
        if not product:
            raise ValueError("Produto não encontrado")
        
        # Atualizar campos
        for key, value in product_data.items():
            if hasattr(product, key) and value is not None:
                setattr(product, key, value)
        
        product.updated_at = datetime.utcnow()
        
        db.commit()
        db.refresh(product)
        
        logger.info(f"Produto atualizado: {product.name}")
        return product
        
    except Exception as e:
        logger.error(f"Erro ao atualizar produto {product_id}: {e}")
        db.rollback()
        raise

def delete_product(db: Session, product_id: int) -> bool:
    """Deletar produto"""
    try:
        product = db.query(Product).filter(Product.id == product_id).first()
        if not product:
            return False
        
        # Verificar se há licenças ativas
        active_licenses = db.query(License).filter(
            License.product_id == product_id,
            License.status == "active",
            License.expires_at > datetime.utcnow()
        ).count()
        
        if active_licenses > 0:
            # Apenas desativar se há licenças ativas
            product.is_active = False
            product.updated_at = datetime.utcnow()
        else:
            # Deletar se não há licenças ativas
            db.delete(product)
        
        db.commit()
        
        logger.info(f"Produto deletado/desativado: {product.name}")
        return True
        
    except Exception as e:
        logger.error(f"Erro ao deletar produto {product_id}: {e}")
        db.rollback()
        return False

def create_category(db: Session, category_data: dict) -> Category:
    """Criar nova categoria"""
    try:
        category = Category(
            name=category_data["name"],
            description=category_data.get("description"),
            icon=category_data.get("icon", "fa-folder")
        )
        
        db.add(category)
        db.commit()
        db.refresh(category)
        
        logger.info(f"Categoria criada: {category.name}")
        return category
        
    except Exception as e:
        logger.error(f"Erro ao criar categoria: {e}")
        db.rollback()
        raise

def update_user_status(db: Session, user_id: int, is_active: bool, is_admin: bool = None) -> User:
    """Atualizar status do usuário"""
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError("Usuário não encontrado")
        
        user.is_active = is_active
        if is_admin is not None:
            user.is_admin = is_admin
        user.updated_at = datetime.utcnow()
        
        db.commit()
        db.refresh(user)
        
        logger.info(f"Status do usuário atualizado: {user.username}")
        return user
        
    except Exception as e:
        logger.error(f"Erro ao atualizar usuário {user_id}: {e}")
        db.rollback()
        raise

def get_user_details(db: Session, user_id: int) -> dict:
    """Obter detalhes completos do usuário"""
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return None
        
        # Licenças do usuário
        licenses = db.query(License).filter(License.user_id == user_id).all()
        
        # Transações do usuário
        transactions = db.query(Transaction).filter(
            Transaction.user_id == user_id
        ).order_by(desc(Transaction.created_at)).limit(10).all()
        
        # Downloads do usuário
        downloads = db.query(Download).filter(
            Download.user_id == user_id
        ).order_by(desc(Download.downloaded_at)).limit(10).all()
        
        # Estatísticas do usuário
        total_spent = db.query(func.sum(Transaction.amount)).filter(
            Transaction.user_id == user_id,
            Transaction.status == "approved"
        ).scalar() or 0
        
        active_licenses_count = len([l for l in licenses if l.status == "active" and not l.is_expired])
        
        return {
            "user": user,
            "licenses": licenses,
            "transactions": transactions,
            "downloads": downloads,
            "stats": {
                "total_spent": total_spent,
                "active_licenses": active_licenses_count,
                "total_downloads": len(downloads)
            }
        }
        
    except Exception as e:
        logger.error(f"Erro ao obter detalhes do usuário {user_id}: {e}")
        return None

def suspend_license(db: Session, license_id: int, reason: str = None) -> bool:
    """Suspender licença"""
    try:
        license_obj = db.query(License).filter(License.id == license_id).first()
        if not license_obj:
            return False
        
        license_obj.status = "suspended"
        db.commit()
        
        logger.info(f"Licença suspensa: {license_obj.license_key} - Motivo: {reason}")
        return True
        
    except Exception as e:
        logger.error(f"Erro ao suspender licença {license_id}: {e}")
        db.rollback()
        return False

def reactivate_license(db: Session, license_id: int) -> bool:
    """Reativar licença"""
    try:
        license_obj = db.query(License).filter(License.id == license_id).first()
        if not license_obj:
            return False
        
        # Verificar se não está expirada
        if license_obj.is_expired:
            return False
        
        license_obj.status = "active"
        db.commit()
        
        logger.info(f"Licença reativada: {license_obj.license_key}")
        return True
        
    except Exception as e:
        logger.error(f"Erro ao reativar licença {license_id}: {e}")
        db.rollback()
        return False

def get_system_logs(db: Session, limit: int = 100) -> list:
    """Obter logs do sistema"""
    try:
        from models import SecurityLog
        
        logs = db.query(SecurityLog).order_by(
            desc(SecurityLog.created_at)
        ).limit(limit).all()
        
        return logs
        
    except Exception as e:
        logger.error(f"Erro ao obter logs: {e}")
        return []

def export_user_data(db: Session, user_id: int) -> dict:
    """Exportar dados do usuário (LGPD/GDPR)"""
    try:
        user_details = get_user_details(db, user_id)
        if not user_details:
            return None
        
        # Serializar dados para exportação
        export_data = {
            "user_info": {
                "username": user_details["user"].username,
                "email": user_details["user"].email,
                "created_at": user_details["user"].created_at.isoformat(),
                "last_login": user_details["user"].last_login.isoformat() if user_details["user"].last_login else None
            },
            "licenses": [
                {
                    "license_key": l.license_key,
                    "product_name": l.product.name,
                    "status": l.status,
                    "created_at": l.created_at.isoformat(),
                    "expires_at": l.expires_at.isoformat()
                }
                for l in user_details["licenses"]
            ],
            "transactions": [
                {
                    "amount": t.amount,
                    "status": t.status,
                    "created_at": t.created_at.isoformat()
                }
                for t in user_details["transactions"]
            ],
            "downloads": [
                {
                    "product_name": d.product.name,
                    "downloaded_at": d.downloaded_at.isoformat()
                }
                for d in user_details["downloads"]
            ]
        }
        
        return export_data
        
    except Exception as e:
        logger.error(f"Erro ao exportar dados do usuário {user_id}: {e}")
        return None
