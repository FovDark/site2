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
from models import User, Product, Category, License
from config import get_config
from auth import hash_password, verify_password, create_access_token, verify_token

# Obter configurações
config = get_config()

# Inicializar FastAPI
app = FastAPI(
    title="FovDark Gaming - Downloads & Digital Licenses",
    description="Plataforma gaming para downloads de software e licenças digitais",
    version="2.0.0",
    debug=config.DEBUG
)

# Configurar middleware com configurações de produção
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS if config.is_production() else ["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=config.ALLOWED_HOSTS if config.is_production() else ["*"]
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

@app.get("/products")
async def products_page(request: Request, db: Session = Depends(get_db)):
    """Página de produtos"""
    try:
        current_user = get_current_user_simple(request, db)
        
        # Buscar produtos com categorias
        products = db.query(Product).join(Category).filter(Product.is_active == True).all()
        categories = db.query(Category).filter(Category.is_active == True).all()
        
        return templates.TemplateResponse("products.html", {
            "request": request,
            "current_user": current_user,
            "products": products,
            "categories": categories
        })
    except Exception as e:
        logger.error(f"Erro ao carregar produtos: {e}")
        return templates.TemplateResponse("error.html", {
            "request": request,
            "error": "Erro ao carregar produtos"
        })

@app.get("/categories")
async def categories_page(request: Request, db: Session = Depends(get_db)):
    """Página de categorias"""
    try:
        current_user = get_current_user_simple(request, db)
        categories = db.query(Category).filter(Category.is_active == True).all()
        
        return templates.TemplateResponse("categories.html", {
            "request": request,
            "current_user": current_user,
            "categories": categories
        })
    except Exception as e:
        logger.error(f"Erro ao carregar categorias: {e}")
        return templates.TemplateResponse("error.html", {
            "request": request,
            "error": "Erro ao carregar categorias"
        })

@app.get("/downloads")
async def downloads_page(request: Request, db: Session = Depends(get_db)):
    """Página de downloads do usuário"""
    try:
        current_user = get_current_user_simple(request, db)
        if not current_user:
            return RedirectResponse(url="/login", status_code=302)
        
        # Buscar licenças ativas do usuário
        licenses = db.query(License).filter(
            License.user_id == current_user.id,
            License.is_active == True
        ).join(Product).all()
        
        return templates.TemplateResponse("downloads.html", {
            "request": request,
            "current_user": current_user,
            "licenses": licenses
        })
    except Exception as e:
        logger.error(f"Erro ao carregar downloads: {e}")
        return templates.TemplateResponse("error.html", {
            "request": request,
            "error": "Erro ao carregar downloads"
        })

@app.get("/products/{product_id}")
async def product_detail(request: Request, product_id: int, db: Session = Depends(get_db)):
    """Página de detalhes do produto"""
    try:
        current_user = get_current_user_simple(request, db)
        
        product = db.query(Product).filter(Product.id == product_id).first()
        if not product:
            return templates.TemplateResponse("error.html", {
                "request": request,
                "error": "Produto não encontrado"
            })
        
        # Verificar se usuário já possui licença
        user_license = None
        if current_user:
            user_license = db.query(License).filter(
                License.user_id == current_user.id,
                License.product_id == product_id,
                License.is_active == True
            ).first()
        
        return templates.TemplateResponse("product_detail.html", {
            "request": request,
            "current_user": current_user,
            "product": product,
            "user_license": user_license
        })
    except Exception as e:
        logger.error(f"Erro ao carregar produto: {e}")
        return templates.TemplateResponse("error.html", {
            "request": request,
            "error": "Erro ao carregar produto"
        })

@app.post("/api/purchase/{product_id}")
async def api_purchase_product(request: Request, product_id: int, db: Session = Depends(get_db)):
    """API para comprar produto"""
    try:
        current_user = get_current_user_simple(request, db)
        if not current_user:
            return JSONResponse(
                status_code=401,
                content={"success": False, "message": "Login necessário"}
            )
        
        product = db.query(Product).filter(Product.id == product_id).first()
        if not product:
            return JSONResponse(
                status_code=404,
                content={"success": False, "message": "Produto não encontrado"}
            )
        
        # Verificar se já possui licença ativa
        existing_license = db.query(License).filter(
            License.user_id == current_user.id,
            License.product_id == product_id,
            License.is_active == True
        ).first()
        
        if existing_license:
            return JSONResponse(
                status_code=400,
                content={"success": False, "message": "Você já possui uma licença ativa para este produto"}
            )
        
        # Criar licença diretamente (simulando pagamento aprovado)
        from license import create_license
        license_obj = create_license(db, current_user.id, product_id, product.duration_days)
        
        if license_obj:
            return JSONResponse(content={
                "success": True,
                "message": "Produto comprado com sucesso!",
                "license_key": license_obj.license_key
            })
        else:
            return JSONResponse(
                status_code=500,
                content={"success": False, "message": "Erro ao processar compra"}
            )
        
    except Exception as e:
        logger.error(f"Erro na compra: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "message": "Erro interno do servidor"}
        )

@app.get("/api/download/{product_id}")
async def api_download_product(request: Request, product_id: int, db: Session = Depends(get_db)):
    """API para download de produto"""
    try:
        current_user = get_current_user_simple(request, db)
        if not current_user:
            return RedirectResponse(url="/login")
        
        # Verificar licença ativa
        license_obj = db.query(License).filter(
            License.user_id == current_user.id,
            License.product_id == product_id,
            License.is_active == True
        ).first()
        
        if not license_obj:
            return templates.TemplateResponse("error.html", {
                "request": request,
                "error": "Você não possui licença para este produto"
            })
        
        product = db.query(Product).filter(Product.id == product_id).first()
        
        if product and product.download_url:
            return RedirectResponse(url=product.download_url)
        else:
            return templates.TemplateResponse("error.html", {
                "request": request,
                "error": "Download não disponível para este produto"
            })
        
    except Exception as e:
        logger.error(f"Erro no download: {e}")
        return templates.TemplateResponse("error.html", {
            "request": request,
            "error": "Erro ao processar download"
        })

@app.get("/contact")
async def contact_page(request: Request, db: Session = Depends(get_db)):
    """Página de contato"""
    current_user = get_current_user_simple(request, db)
    return templates.TemplateResponse("contact.html", {
        "request": request,
        "current_user": current_user
    })

@app.get("/support")
async def support_page(request: Request, db: Session = Depends(get_db)):
    """Página de suporte"""
    current_user = get_current_user_simple(request, db)
    return templates.TemplateResponse("support.html", {
        "request": request,
        "current_user": current_user
    })

@app.get("/terms")
async def terms_page(request: Request, db: Session = Depends(get_db)):
    """Página de termos de uso"""
    current_user = get_current_user_simple(request, db)
    return templates.TemplateResponse("terms.html", {
        "request": request,
        "current_user": current_user
    })

@app.get("/privacy")
async def privacy_page(request: Request, db: Session = Depends(get_db)):
    """Página de política de privacidade"""
    current_user = get_current_user_simple(request, db)
    return templates.TemplateResponse("privacy.html", {
        "request": request,
        "current_user": current_user
    })

@app.get("/products", response_class=HTMLResponse)
async def products_page(request: Request, db: Session = Depends(get_db)):
    """Página de produtos"""
    current_user = get_current_user_simple(request, db)
    
    # Buscar todos os produtos ativos
    products = db.query(Product).filter(Product.is_active == True).all()
    
    return templates.TemplateResponse("products.html", {
        "request": request,
        "current_user": current_user,
        "products": products
    })

@app.get("/categories", response_class=HTMLResponse)
async def categories_page(request: Request, db: Session = Depends(get_db)):
    """Página de categorias"""
    current_user = get_current_user_simple(request, db)
    
    # Buscar categorias ativas
    categories = db.query(Category).filter(Category.is_active == True).all()
    
    return templates.TemplateResponse("categories.html", {
        "request": request,
        "current_user": current_user,
        "categories": categories
    })

@app.get("/profile", response_class=HTMLResponse)
async def profile_page(request: Request, db: Session = Depends(get_db)):
    """Página de perfil do usuário"""
    current_user = get_current_user_simple(request, db)
    
    if not current_user:
        return RedirectResponse(url="/login", status_code=302)
    
    return templates.TemplateResponse("profile.html", {
        "request": request,
        "current_user": current_user
    })

@app.get("/faq", response_class=HTMLResponse)
async def faq_page(request: Request, db: Session = Depends(get_db)):
    """Página de FAQ"""
    current_user = get_current_user_simple(request, db)
    
    return templates.TemplateResponse("faq.html", {
        "request": request,
        "current_user": current_user
    })

@app.get("/status", response_class=HTMLResponse)
async def status_page(request: Request, db: Session = Depends(get_db)):
    """Página de status do sistema"""
    current_user = get_current_user_simple(request, db)
    
    return templates.TemplateResponse("status.html", {
        "request": request,
        "current_user": current_user
    })

@app.get("/health")
async def health_check():
    """Health check da aplicação"""
    return {"status": "ok", "message": "FovDark está funcionando"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)