"""
Versão simplificada do main.py para resolver problemas de importação
"""
import os
import logging
from fastapi import FastAPI, Request, Depends, Form, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from sqlalchemy.orm import Session

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Importações locais
from database import get_db, init_db
from models import User, Product, Category
from auth import hash_password, verify_password, create_access_token, verify_token

# Inicializar FastAPI
app = FastAPI(
    title="FovDark - Sistema de Licenças Digitais",
    description="Plataforma completa para venda de licenças digitais",
    version="1.0.0"
)

# Configurar middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["*"]
)

# Configurar arquivos estáticos e templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Função para obter usuário atual
def get_current_user_simple(request: Request, db: Session = Depends(get_db)):
    """Obter usuário atual de forma simplificada"""
    try:
        # Tentar obter token do cookie
        auth_cookie = request.cookies.get("access_token")
        if auth_cookie and auth_cookie.startswith("Bearer "):
            token = auth_cookie[7:]
            username = verify_token(token)
            if username:
                user = db.query(User).filter(User.username == username).first()
                if user and user.is_active:
                    return user
    except:
        pass
    return None

@app.on_event("startup")
async def startup_event():
    """Inicializar aplicação"""
    try:
        logger.info("Iniciando aplicação FovDark...")
        init_db()
        logger.info("Banco de dados inicializado com sucesso")
    except Exception as e:
        logger.error(f"Erro ao inicializar aplicação: {e}")

@app.get("/", response_class=HTMLResponse)
async def index(request: Request, db: Session = Depends(get_db)):
    """Página inicial"""
    current_user = get_current_user_simple(request, db)
    
    # Buscar produtos em destaque
    featured_products = db.query(Product).filter(
        Product.is_active == True,
        Product.is_featured == True
    ).limit(6).all()
    
    # Buscar categorias
    categories = db.query(Category).filter(Category.is_active == True).all()
    
    return templates.TemplateResponse("index.html", {
        "request": request,
        "current_user": current_user,
        "featured_products": featured_products,
        "categories": categories
    })

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Página de login"""
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/login")
async def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    """Processar login"""
    try:
        # Buscar usuário
        user = db.query(User).filter(User.username == username).first()
        if not user or not verify_password(password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Usuário ou senha incorretos"
            )
        
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Conta desativada"
            )
        
        # Criar token de acesso
        access_token = create_access_token(data={"sub": user.username})
        
        # Redirecionar para o painel
        response = RedirectResponse(url="/painel", status_code=302)
        response.set_cookie(
            key="access_token",
            value=f"Bearer {access_token}",
            httponly=True,
            max_age=1800,  # 30 minutos
            secure=False  # True em produção com HTTPS
        )
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro no login: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno do servidor"
        )

@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    """Página de registro"""
    return templates.TemplateResponse("register.html", {"request": request})

@app.post("/register")
async def register(
    request: Request,
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    confirm_password: str = Form(...),
    db: Session = Depends(get_db)
):
    """Registrar novo usuário"""
    try:
        # Validações básicas
        if password != confirm_password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Senhas não coincidem"
            )
        
        if len(password) < 6:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Senha deve ter pelo menos 6 caracteres"
            )
        
        # Verificar se usuário já existe
        existing_user = db.query(User).filter(
            (User.username == username) | (User.email == email)
        ).first()
        
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Usuário ou email já existe"
            )
        
        # Criar novo usuário
        new_user = User(
            username=username,
            email=email,
            password_hash=hash_password(password),
            is_active=True,
            is_admin=False
        )
        
        db.add(new_user)
        db.commit()
        
        # Redirecionar para login
        return RedirectResponse(url="/login?message=Conta criada com sucesso", status_code=302)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro no registro: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno do servidor"
        )

@app.get("/painel", response_class=HTMLResponse)
async def painel(request: Request, db: Session = Depends(get_db)):
    """Painel do usuário"""
    current_user = get_current_user_simple(request, db)
    if not current_user:
        return RedirectResponse(url="/login", status_code=302)
    
    return templates.TemplateResponse("painel.html", {
        "request": request,
        "current_user": current_user
    })

@app.get("/admin", response_class=HTMLResponse)
async def admin_panel(request: Request, db: Session = Depends(get_db)):
    """Painel administrativo"""
    current_user = get_current_user_simple(request, db)
    if not current_user or not current_user.is_admin:
        return RedirectResponse(url="/login", status_code=302)
    
    # Buscar estatísticas básicas
    stats = {
        "users": {"total": db.query(User).count()},
        "products": {"total": db.query(Product).count()},
        "categories": {"total": db.query(Category).count()}
    }
    
    # Buscar dados para exibir
    users = db.query(User).limit(10).all()
    products = db.query(Product).limit(10).all()
    categories = db.query(Category).all()
    
    return templates.TemplateResponse("admin.html", {
        "request": request,
        "current_user": current_user,
        "stats": stats,
        "users": users,
        "products": products,
        "categories": categories
    })

@app.get("/logout")
async def logout():
    """Logout do usuário"""
    response = RedirectResponse(url="/", status_code=302)
    response.delete_cookie(key="access_token")
    return response

@app.get("/health")
async def health_check():
    """Health check da aplicação"""
    return {"status": "ok", "message": "FovDark está funcionando"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)