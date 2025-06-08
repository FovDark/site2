import os
import jwt
from datetime import datetime, timedelta
from passlib.context import CryptContext
from fastapi import HTTPException, status, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from models import User
import logging

logger = logging.getLogger(__name__)

# Configurações
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "fovdark-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Contexto de criptografia
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Bearer token security
security = HTTPBearer(auto_error=False)

def hash_password(password: str) -> str:
    """Hash da senha usando bcrypt"""
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verificar senha"""
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict, expires_delta: timedelta = None):
    """Criar token JWT de acesso"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(token: str):
    """Verificar e decodificar token JWT"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            return None
        return username
    except jwt.PyJWTError:
        return None

def authenticate_user(db: Session, username: str, password: str):
    """Autenticar usuário - compatível com Supabase"""
    user = db.query(User).filter(User.email == username).first()
    if not user:
        return False
    if not verify_password(password, user.senha_hash):
        return False
    
    # Atualizar último login
    user.ultimo_login = datetime.utcnow()
    db.commit()
    
    return user

def get_current_user(request: Request, db: Session):
    """Obter usuário atual a partir do token"""
    # Tentar obter token do cookie primeiro
    token = None
    auth_cookie = request.cookies.get("access_token")
    
    if auth_cookie and auth_cookie.startswith("Bearer "):
        token = auth_cookie[7:]  # Remove "Bearer "
    else:
        # Fallback para header Authorization
        credentials: HTTPAuthorizationCredentials = security(request)
        if credentials:
            token = credentials.credentials
    
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de acesso não encontrado"
        )
    
    username = verify_token(token)
    if username is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido"
        )
    
    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuário não encontrado"
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuário inativo"
        )
    
    return user

def get_current_admin_user(current_user: User):
    """Obter usuário admin atual"""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso negado - privilégios de administrador necessários"
        )
    return current_user

def create_user_token(user: User) -> str:
    """Criar token para um usuário específico"""
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, 
        expires_delta=access_token_expires
    )
    return access_token

def validate_password_strength(password: str) -> bool:
    """Validar força da senha"""
    if len(password) < 8:
        return False
    
    has_upper = any(c.isupper() for c in password)
    has_lower = any(c.islower() for c in password)
    has_digit = any(c.isdigit() for c in password)
    
    return has_upper and has_lower and has_digit

def generate_secure_password(length: int = 12) -> str:
    """Gerar senha segura aleatória"""
    import secrets
    import string
    
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    password = ''.join(secrets.choice(alphabet) for _ in range(length))
    return password

class AuthManager:
    """Gerenciador de autenticação"""
    
    def __init__(self):
        self.pwd_context = pwd_context
        self.secret_key = SECRET_KEY
        self.algorithm = ALGORITHM
    
    def hash_password(self, password: str) -> str:
        """Hash da senha"""
        return self.pwd_context.hash(password)
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verificar senha"""
        return self.pwd_context.verify(plain_password, hashed_password)
    
    def create_token(self, user_data: dict, expires_delta: timedelta = None) -> str:
        """Criar token JWT"""
        to_encode = user_data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt
    
    def verify_token(self, token: str) -> dict:
        """Verificar token JWT"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except jwt.PyJWTError as e:
            logger.error(f"Erro ao verificar token: {e}")
            return None
    
    def authenticate_user(self, db: Session, username: str, password: str) -> User:
        """Autenticar usuário"""
        try:
            user = db.query(User).filter(User.username == username).first()
            if not user:
                return None
            
            if not self.verify_password(password, user.password_hash):
                return None
            
            if not user.is_active:
                return None
            
            # Atualizar último login
            user.last_login = datetime.utcnow()
            db.commit()
            
            return user
            
        except Exception as e:
            logger.error(f"Erro na autenticação: {e}")
            return None

# Instância global do gerenciador de autenticação
auth_manager = AuthManager()
