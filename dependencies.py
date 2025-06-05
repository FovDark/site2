"""
Dependências centralizadas para evitar importações circulares
"""
from fastapi import HTTPException, status, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from database import get_db
from models import User
import auth

security = HTTPBearer(auto_error=False)

def get_current_user(request: Request, db: Session = Depends(get_db)):
    """Obter usuário atual a partir do token"""
    # Tentar obter token do cookie primeiro
    token = None
    auth_cookie = request.cookies.get("access_token")
    
    if auth_cookie and auth_cookie.startswith("Bearer "):
        token = auth_cookie[7:]  # Remove "Bearer "
    else:
        # Fallback para header Authorization
        try:
            credentials: HTTPAuthorizationCredentials = security(request)
            if credentials:
                token = credentials.credentials
        except:
            pass
    
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de acesso não encontrado"
        )
    
    return auth.get_current_user(request, db)

def get_current_admin_user(current_user: User = Depends(get_current_user)):
    """Obter usuário admin atual"""
    return auth.get_current_admin_user(current_user)