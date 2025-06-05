import uuid
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from models import PasswordReset, User
from email_utils import send_password_reset_email
from auth import hash_password
import logging

logger = logging.getLogger(__name__)

def create_reset_token(user_id: int) -> str:
    """Criar token de reset de senha"""
    try:
        # Gerar token único
        token = str(uuid.uuid4()).replace("-", "")
        
        # Definir expiração (1 hora)
        expires_at = datetime.utcnow() + timedelta(hours=1)
        
        # Criar registro de reset
        reset_record = PasswordReset(
            user_id=user_id,
            token=token,
            expires_at=expires_at
        )
        
        # Salvar no banco (assumindo que temos acesso à sessão)
        # Nota: Esta função deve receber a sessão como parâmetro
        
        return token
        
    except Exception as e:
        logger.error(f"Erro ao criar token de reset: {e}")
        return None

def verify_reset_token(db: Session, token: str) -> User:
    """Verificar token de reset e retornar usuário"""
    try:
        # Buscar token válido
        reset_record = db.query(PasswordReset).filter(
            PasswordReset.token == token,
            PasswordReset.is_used == False,
            PasswordReset.expires_at > datetime.utcnow()
        ).first()
        
        if not reset_record:
            logger.warning(f"Token de reset inválido ou expirado: {token}")
            return None
        
        # Buscar usuário
        user = db.query(User).filter(User.id == reset_record.user_id).first()
        
        if not user:
            logger.error(f"Usuário não encontrado para token: {token}")
            return None
        
        return user
        
    except Exception as e:
        logger.error(f"Erro ao verificar token de reset: {e}")
        return None

def use_reset_token(db: Session, token: str, new_password: str) -> bool:
    """Usar token de reset para definir nova senha"""
    try:
        # Verificar token
        user = verify_reset_token(db, token)
        if not user:
            return False
        
        # Buscar registro de reset
        reset_record = db.query(PasswordReset).filter(
            PasswordReset.token == token,
            PasswordReset.is_used == False
        ).first()
        
        if not reset_record:
            return False
        
        # Atualizar senha do usuário
        user.password_hash = hash_password(new_password)
        user.updated_at = datetime.utcnow()
        
        # Marcar token como usado
        reset_record.is_used = True
        
        # Invalidar outros tokens do usuário
        other_tokens = db.query(PasswordReset).filter(
            PasswordReset.user_id == user.id,
            PasswordReset.is_used == False,
            PasswordReset.id != reset_record.id
        ).all()
        
        for token_record in other_tokens:
            token_record.is_used = True
        
        db.commit()
        
        logger.info(f"Senha alterada com sucesso para usuário: {user.username}")
        return True
        
    except Exception as e:
        logger.error(f"Erro ao usar token de reset: {e}")
        db.rollback()
        return False

def cleanup_expired_tokens(db: Session) -> int:
    """Limpar tokens expirados"""
    try:
        expired_tokens = db.query(PasswordReset).filter(
            PasswordReset.expires_at <= datetime.utcnow(),
            PasswordReset.is_used == False
        ).all()
        
        count = 0
        for token_record in expired_tokens:
            token_record.is_used = True
            count += 1
        
        db.commit()
        
        if count > 0:
            logger.info(f"Limpeza realizada: {count} tokens de reset expirados")
        
        return count
        
    except Exception as e:
        logger.error(f"Erro na limpeza de tokens expirados: {e}")
        db.rollback()
        return 0

def request_password_reset(db: Session, email: str) -> bool:
    """Solicitar reset de senha por email"""
    try:
        # Buscar usuário por email
        user = db.query(User).filter(User.email == email).first()
        
        if not user:
            # Por segurança, sempre retornar True mesmo se o usuário não existir
            logger.warning(f"Tentativa de reset para email não cadastrado: {email}")
            return True
        
        # Verificar se há tokens recentes (últimos 5 minutos)
        recent_time = datetime.utcnow() - timedelta(minutes=5)
        recent_tokens = db.query(PasswordReset).filter(
            PasswordReset.user_id == user.id,
            PasswordReset.created_at >= recent_time
        ).count()
        
        if recent_tokens > 0:
            logger.warning(f"Rate limit: muitos tokens recentes para usuário {user.username}")
            return True  # Retornar True por segurança
        
        # Gerar token
        token = str(uuid.uuid4()).replace("-", "")
        expires_at = datetime.utcnow() + timedelta(hours=1)
        
        # Criar registro de reset
        reset_record = PasswordReset(
            user_id=user.id,
            token=token,
            expires_at=expires_at
        )
        
        db.add(reset_record)
        db.commit()
        
        # Enviar email
        email_sent = send_password_reset_email(user.email, token)
        
        if email_sent:
            logger.info(f"Email de reset enviado para: {email}")
        else:
            logger.error(f"Falha ao enviar email de reset para: {email}")
        
        return True
        
    except Exception as e:
        logger.error(f"Erro ao solicitar reset de senha: {e}")
        db.rollback()
        return False

def get_user_reset_tokens(db: Session, user_id: int) -> list:
    """Obter tokens de reset do usuário"""
    try:
        tokens = db.query(PasswordReset).filter(
            PasswordReset.user_id == user_id
        ).order_by(PasswordReset.created_at.desc()).all()
        
        return tokens
        
    except Exception as e:
        logger.error(f"Erro ao obter tokens do usuário {user_id}: {e}")
        return []

def invalidate_user_tokens(db: Session, user_id: int) -> bool:
    """Invalidar todos os tokens de reset do usuário"""
    try:
        tokens = db.query(PasswordReset).filter(
            PasswordReset.user_id == user_id,
            PasswordReset.is_used == False
        ).all()
        
        count = 0
        for token in tokens:
            token.is_used = True
            count += 1
        
        db.commit()
        
        logger.info(f"Invalidados {count} tokens para usuário {user_id}")
        return True
        
    except Exception as e:
        logger.error(f"Erro ao invalidar tokens do usuário {user_id}: {e}")
        db.rollback()
        return False

class PasswordResetManager:
    """Gerenciador de reset de senha"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def request_reset(self, email: str) -> bool:
        """Solicitar reset de senha"""
        return request_password_reset(self.db, email)
    
    def verify_token(self, token: str) -> User:
        """Verificar token"""
        return verify_reset_token(self.db, token)
    
    def reset_password(self, token: str, new_password: str) -> bool:
        """Redefinir senha"""
        return use_reset_token(self.db, token, new_password)
    
    def cleanup_expired(self) -> int:
        """Limpar tokens expirados"""
        return cleanup_expired_tokens(self.db)
    
    def invalidate_user_tokens(self, user_id: int) -> bool:
        """Invalidar tokens do usuário"""
        return invalidate_user_tokens(self.db, user_id)
