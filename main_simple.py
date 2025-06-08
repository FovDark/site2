"""
Versão simplificada do main.py para resolver problemas de importação
"""
import os
import logging
from datetime import datetime
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
            payload = verify_token(token)
            if payload:
                # O token contém email no campo 'sub'
                email = payload.get("sub")
                if email:
                    user = db.query(User).filter(User.email == email).first()
                    if user and user.is_active:
                        return user
    except Exception as e:
        logger.error(f"Erro na autenticação: {e}")
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
        # Buscar usuário por email ou username
        user = db.query(User).filter(
            (User.email == username) | (User.username == username)
        ).first()
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
        
        # Atualizar último login
        user.ultimo_login = datetime.utcnow()
        db.commit()
        
        # Criar token de acesso
        access_token = create_access_token(data={"sub": user.email})
        
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
    
    # Buscar licenças do usuário
    user_licenses = db.query(License).filter(
        License.user_id == current_user.id
    ).join(Product).join(Category).all()
    
    # Buscar estatísticas básicas
    total_licenses = len(user_licenses)
    active_licenses = len([l for l in user_licenses if l.status == "active"])
    
    return templates.TemplateResponse("painel.html", {
        "request": request,
        "current_user": current_user,
        "licenses": user_licenses,
        "total_licenses": total_licenses,
        "active_licenses": active_licenses,
        "downloads": [],  # Por enquanto vazio
        "transactions": []  # Por enquanto vazio
    })

@app.get("/admin", response_class=HTMLResponse)
async def admin_panel(request: Request, db: Session = Depends(get_db)):
    """Painel administrativo"""
    current_user = get_current_user_simple(request, db)
    if not current_user or not current_user.is_admin:
        return RedirectResponse(url="/login", status_code=302)
    
    # Buscar estatísticas
    total_users = db.query(User).count()
    total_products = db.query(Product).count()
    active_licenses = db.query(License).filter(License.status == "active").count()
    
    # Buscar produtos para exibição
    products = db.query(Product).all()
    categories = db.query(Category).all()
    
    stats = {
        'total_users': total_users,
        'total_products': total_products,
        'total_sales': 0.0,
        'active_licenses': active_licenses
    }
    
    return templates.TemplateResponse("admin_new.html", {
        "request": request,
        "current_user": current_user,
        "stats": stats,
        "products": products,
        "categories": categories
    })

@app.get("/logout")
async def logout():
    """Logout do usuário"""
    response = RedirectResponse(url="/", status_code=302)
    response.delete_cookie(key="access_token")
    return response

@app.get("/contact")
async def contact_page(request: Request, db: Session = Depends(get_db)):
    """Página de contato"""
    current_user = get_current_user_simple(request, db)
    return templates.TemplateResponse("contact.html", {
        "request": request,
        "current_user": current_user
    })

@app.post("/api/verify-license")
async def api_verify_license(request: Request, license_key: str = Form(...), hwid: str = Form(None), db: Session = Depends(get_db)):
    """API para verificar licença"""
    try:
        from license import verify_license
        is_valid, license_obj = verify_license(db, license_key, hwid)
        
        if is_valid and license_obj:
            return JSONResponse({
                "success": True,
                "valid": True,
                "license": {
                    "id": license_obj.id,
                    "product_id": license_obj.product_id,
                    "expires_at": license_obj.expires_at.isoformat() if license_obj.expires_at else None,
                    "status": license_obj.status
                }
            })
        else:
            return JSONResponse({
                "success": True,
                "valid": False,
                "message": "Licença inválida ou expirada"
            })
    except Exception as e:
        logger.error(f"Erro ao verificar licença: {e}")
        return JSONResponse({
            "success": False,
            "valid": False,
            "message": "Erro interno do servidor"
        }, status_code=500)

@app.get("/api/download/{product_id}")
async def api_download_product(request: Request, product_id: int, current_user: User = Depends(get_current_user_simple), db: Session = Depends(get_db)):
    """API para fazer download de produto"""
    try:
        if not current_user:
            return JSONResponse({
                "success": False,
                "message": "Login necessário"
            }, status_code=401)
        
        # Verificar se usuário tem licença ativa para o produto
        license_obj = db.query(License).filter(
            License.user_id == current_user.id,
            License.product_id == product_id,
            License.status == "active"
        ).first()
        
        if not license_obj or license_obj.is_expired:
            return JSONResponse({
                "success": False,
                "message": "Você não possui licença ativa para este produto"
            }, status_code=403)
        
        product = db.query(Product).filter(Product.id == product_id).first()
        if not product or not product.download_url:
            return JSONResponse({
                "success": False,
                "message": "Download não disponível"
            }, status_code=404)
        
        # Incrementar contador de downloads
        product.download_count += 1
        db.commit()
        
        return JSONResponse({
            "success": True,
            "download_url": product.download_url,
            "product_name": product.name,
            "license_key": license_obj.license_key,
            "expires_at": license_obj.expires_at.isoformat()
        })
        
    except Exception as e:
        logger.error(f"Erro no download: {e}")
        return JSONResponse({
            "success": False,
            "message": "Erro interno do servidor"
        }, status_code=500)

@app.get("/download/file/{product_id}")
async def secure_download_file(request: Request, product_id: int, current_user: User = Depends(get_current_user_simple), db: Session = Depends(get_db)):
    """Download seguro de arquivo do produto"""
    try:
        if not current_user:
            return JSONResponse({
                "success": False,
                "message": "Acesso não autorizado"
            }, status_code=401)
        
        # Verificar licença ativa
        license_obj = db.query(License).filter(
            License.user_id == current_user.id,
            License.product_id == product_id,
            License.status == "active"
        ).first()
        
        if not license_obj or license_obj.is_expired:
            return JSONResponse({
                "success": False,
                "message": "Licença expirada ou inválida"
            }, status_code=403)
        
        product = db.query(Product).filter(Product.id == product_id).first()
        if not product or not product.download_url:
            return JSONResponse({
                "success": False,
                "message": "Arquivo não encontrado"
            }, status_code=404)
        
        # Construir caminho do arquivo
        file_path = f".{product.download_url}"
        
        from fastapi.responses import FileResponse
        import os
        
        if not os.path.exists(file_path):
            return JSONResponse({
                "success": False,
                "message": "Arquivo não encontrado no servidor"
            }, status_code=404)
        
        # Registrar download
        from models import Download
        download_record = Download(
            user_id=current_user.id,
            license_id=license_obj.id,
            product_id=product_id,
            ip_address=request.client.host,
            downloaded_at=datetime.utcnow()
        )
        db.add(download_record)
        
        # Incrementar contador
        product.download_count += 1
        db.commit()
        
        # Determinar nome do arquivo para download
        filename = f"FovDark_{product.name.replace(' ', '_')}.exe"
        
        return FileResponse(
            path=file_path,
            filename=filename,
            media_type="application/octet-stream"
        )
        
    except Exception as e:
        logger.error(f"Erro no download seguro: {e}")
        return JSONResponse({
            "success": False,
            "message": "Erro interno do servidor"
        }, status_code=500)

@app.get("/api/license/{license_id}/status")
async def api_license_status(request: Request, license_id: int, current_user: User = Depends(get_current_user_simple), db: Session = Depends(get_db)):
    """API para obter status da licença em tempo real"""
    try:
        if not current_user:
            return JSONResponse({
                "success": False,
                "message": "Login necessário"
            }, status_code=401)
        
        # Buscar licença do usuário
        license_obj = db.query(License).filter(
            License.id == license_id,
            License.user_id == current_user.id
        ).first()
        
        if not license_obj:
            return JSONResponse({
                "success": False,
                "message": "Licença não encontrada"
            }, status_code=404)
        
        # Verificar se expirou e atualizar status
        if license_obj.is_expired and license_obj.status == "active":
            license_obj.status = "expired"
            db.commit()
        
        # Retornar dados da licença
        return JSONResponse({
            "success": True,
            "license": {
                "id": license_obj.id,
                "license_key": license_obj.license_key,
                "status": license_obj.status,
                "is_expired": license_obj.is_expired,
                "time_remaining": license_obj.time_remaining,
                "formatted_time": license_obj.formatted_time_remaining,
                "expires_at": license_obj.expires_at.isoformat()
            }
        })
        
    except Exception as e:
        logger.error(f"Erro ao obter status da licença: {e}")
        return JSONResponse({
            "success": False,
            "message": "Erro interno do servidor"
        }, status_code=500)

# ========================
# ROTAS DE PAGAMENTO STRIPE
# ========================

@app.post("/api/stripe/checkout/{product_id}")
async def stripe_checkout_product(
    request: Request,
    product_id: int,
    db: Session = Depends(get_db)
):
    """API para criar checkout do Stripe"""
    try:
        current_user = get_current_user_simple(request, db)
        if not current_user:
            return JSONResponse({
                "success": False,
                "message": "Login necessário"
            }, status_code=401)
        
        # Importar função do Stripe
        from stripe_simple import create_stripe_checkout_session
        
        # Criar sessão de checkout
        result = create_stripe_checkout_session(current_user.id, product_id, db)
        
        if result["success"]:
            return JSONResponse({
                "success": True,
                "checkout_url": result["checkout_url"],
                "session_id": result["session_id"],
                "amount": result["amount"],
                "product_name": result["product_name"]
            })
        else:
            return JSONResponse({
                "success": False,
                "message": result.get("error", "Erro ao criar checkout")
            }, status_code=400)
            
    except Exception as e:
        logger.error(f"Erro no checkout Stripe: {e}")
        return JSONResponse({
            "success": False,
            "message": "Erro interno do servidor"
        }, status_code=500)

@app.post("/api/webhook/stripe")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    """Webhook do Stripe para confirmação de pagamentos"""
    try:
        from stripe_simple import process_stripe_webhook_event
        
        payload = await request.body()
        sig_header = request.headers.get('stripe-signature', '')
        
        # Processar evento
        result = process_stripe_webhook_event(payload, sig_header, db)
        
        if result["success"]:
            return JSONResponse({"status": "success", "message": result.get("message", "Processado")})
        else:
            return JSONResponse({"error": result.get("error", "Erro no processamento")}, status_code=400)
        
    except Exception as e:
        logger.error(f"Erro no webhook Stripe: {e}")
        return JSONResponse({"error": str(e)}, status_code=400)

@app.get("/payment/success")
async def payment_success(request: Request, session_id: str = None, db: Session = Depends(get_db)):
    """Página de sucesso do pagamento"""
    current_user = get_current_user_simple(request, db)
    
    success_data = {
        "payment_confirmed": True,
        "session_id": session_id
    }
    
    return templates.TemplateResponse("payment_success.html", {
        "request": request,
        "current_user": current_user,
        "success_data": success_data
    })

@app.get("/payment/cancel")
async def payment_cancel(request: Request, db: Session = Depends(get_db)):
    """Página de cancelamento do pagamento"""
    current_user = get_current_user_simple(request, db)
    
    return templates.TemplateResponse("payment_cancel.html", {
        "request": request,
        "current_user": current_user
    })

@app.get("/payment/pending")
async def payment_pending(request: Request, db: Session = Depends(get_db)):
    """Página de pagamento pendente"""
    current_user = get_current_user_simple(request, db)
    
    return templates.TemplateResponse("payment_pending.html", {
        "request": request,
        "current_user": current_user
    })

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

@app.get("/category/{category_name}")
async def category_products(request: Request, category_name: str, db: Session = Depends(get_db)):
    """Página de produtos por categoria"""
    try:
        current_user = get_current_user_simple(request, db)
        
        # Buscar categoria por nome (case insensitive)
        category = db.query(Category).filter(
            Category.name.ilike(f"%{category_name}%"),
            Category.is_active == True
        ).first()
        
        if not category:
            # Se não encontrar categoria exata, redirecionar para produtos
            return RedirectResponse(url="/products", status_code=302)
        
        # Buscar produtos da categoria
        products = db.query(Product).filter(
            Product.category_id == category.id,
            Product.is_active == True
        ).all()
        
        # Buscar todas as categorias para o menu
        categories = db.query(Category).filter(Category.is_active == True).all()
        
        return templates.TemplateResponse("products.html", {
            "request": request,
            "current_user": current_user,
            "products": products,
            "categories": categories,
            "selected_category": category,
            "page_title": f"Produtos - {category.name}"
        })
    except Exception as e:
        logger.error(f"Erro ao carregar produtos da categoria: {e}")
        return RedirectResponse(url="/products", status_code=302)

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
            License.status == "active"
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
@app.get("/product/{product_id}")
async def product_detail(request: Request, product_id: int, db: Session = Depends(get_db)):
    """Página de detalhes do produto"""
    try:
        current_user = get_current_user_simple(request, db)
        
        # Buscar produto com categoria
        product = db.query(Product).join(Category).filter(Product.id == product_id).first()
        if not product or not product.is_active:
            return templates.TemplateResponse("error.html", {
                "request": request,
                "current_user": current_user,
                "error": "Produto não encontrado ou indisponível"
            })
        
        # Verificar se usuário já possui licença ativa
        user_license = None
        can_download = False
        if current_user:
            user_license = db.query(License).filter(
                License.user_id == current_user.id,
                License.product_id == product_id,
                License.status == "active"
            ).first()
            can_download = user_license is not None
        
        # Buscar produtos relacionados da mesma categoria
        related_products = db.query(Product).filter(
            Product.category_id == product.category_id,
            Product.id != product_id,
            Product.is_active == True
        ).limit(4).all()
        
        # Formatar preço
        formatted_price = f"R$ {product.price:.2f}".replace(".", ",")
        
        # Processar tags
        tags_list = []
        if product.tags:
            tags_list = [tag.strip() for tag in product.tags.split(",")]
        
        return templates.TemplateResponse("product_detail.html", {
            "request": request,
            "current_user": current_user,
            "product": product,
            "user_license": user_license,
            "can_download": can_download,
            "related_products": related_products,
            "formatted_price": formatted_price,
            "tags_list": tags_list,
            "page_title": f"{product.name} - FovDark Gaming"
        })
    except Exception as e:
        logger.error(f"Erro ao carregar produto {product_id}: {e}")
        return templates.TemplateResponse("error.html", {
            "request": request,
            "current_user": current_user,
            "error": "Erro ao carregar detalhes do produto"
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
            License.status == "active"
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
            License.status == "active"
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

# Admin API Endpoints
@app.post("/api/admin/products")
async def api_create_product(
    request: Request,
    name: str = Form(...),
    description: str = Form(...),
    category_id: int = Form(...),
    price: float = Form(0),
    image_url: str = Form(None),
    download_url: str = Form(None),
    duration_days: int = Form(30),
    tags: str = Form(None),
    requirements: str = Form(None),
    db: Session = Depends(get_db)
):
    """API para criar produto (admin apenas)"""
    try:
        current_user = get_current_user_simple(request, db)
        if not current_user or not current_user.is_admin:
            return JSONResponse(
                status_code=403,
                content={"success": False, "message": "Acesso negado"}
            )
        
        # Verificar se categoria existe
        category = db.query(Category).filter(Category.id == category_id).first()
        if not category:
            return JSONResponse(
                status_code=400,
                content={"success": False, "message": "Categoria não encontrada"}
            )
        
        # Criar produto
        new_product = Product(
            name=name,
            description=description,
            price=price,
            category_id=category_id,
            image_url=image_url if image_url else None,
            download_url=download_url if download_url else None,
            duration_days=duration_days if price > 0 else None,
            tags=tags,
            requirements=requirements,
            is_active=True,
            is_featured=False
        )
        
        db.add(new_product)
        db.commit()
        db.refresh(new_product)
        
        # Sincronizar automaticamente com Stripe se for produto pago
        stripe_result = None
        if price > 0:
            try:
                from stripe_product_sync import auto_sync_product_create
                stripe_result = auto_sync_product_create(new_product, db)
                if not stripe_result['success']:
                    logger.warning(f"Erro na sincronização Stripe: {stripe_result.get('error')}")
            except Exception as e:
                logger.warning(f"Erro na sincronização automática com Stripe: {e}")
        
        response_data = {
            "success": True,
            "message": "Produto criado com sucesso!",
            "product_id": new_product.id
        }
        
        # Adicionar informações do Stripe se sincronizado
        if stripe_result and stripe_result['success']:
            response_data["stripe_synced"] = True
            response_data["stripe_product_id"] = stripe_result.get('stripe_product_id')
        
        return JSONResponse(content=response_data)
        
    except Exception as e:
        logger.error(f"Erro ao criar produto: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "message": "Erro interno do servidor"}
        )

@app.post("/api/admin/sync-stripe")
async def api_sync_stripe_products(
    request: Request,
    db: Session = Depends(get_db)
):
    """API para sincronizar todos os produtos com Stripe (admin apenas)"""
    try:
        current_user = get_current_user_simple(request, db)
        if not current_user or not current_user.is_admin:
            return JSONResponse(
                status_code=403,
                content={"success": False, "message": "Acesso negado"}
            )
        
        # Importar função de sincronização
        from stripe_product_sync import StripeProductManager
        manager = StripeProductManager()
        
        # Sincronizar todos os produtos
        result = manager.sync_all_products(db)
        
        if result['success']:
            return JSONResponse(content={
                "success": True,
                "message": f"Sincronização concluída! {result['synced_count']}/{result['total_products']} produtos sincronizados",
                "synced_count": result['synced_count'],
                "total_products": result['total_products'],
                "errors": result.get('errors', [])
            })
        else:
            return JSONResponse(
                status_code=500,
                content={"success": False, "message": f"Erro na sincronização: {result.get('error')}"}
            )
        
    except Exception as e:
        logger.error(f"Erro na sincronização Stripe: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "message": "Erro interno do servidor"}
        )

@app.put("/api/admin/products/{product_id}")
async def api_update_product(
    request: Request,
    product_id: int,
    name: str = Form(...),
    description: str = Form(...),
    category_id: int = Form(...),
    price: float = Form(0),
    image_url: str = Form(None),
    download_url: str = Form(None),
    duration_days: int = Form(30),
    tags: str = Form(None),
    requirements: str = Form(None),
    is_active: bool = Form(True),
    db: Session = Depends(get_db)
):
    """API para atualizar produto (admin apenas)"""
    try:
        current_user = get_current_user_simple(request, db)
        if not current_user or not current_user.is_admin:
            return JSONResponse(
                status_code=403,
                content={"success": False, "message": "Acesso negado"}
            )
        
        # Buscar produto
        product = db.query(Product).filter(Product.id == product_id).first()
        if not product:
            return JSONResponse(
                status_code=404,
                content={"success": False, "message": "Produto não encontrado"}
            )
        
        # Verificar se categoria existe
        category = db.query(Category).filter(Category.id == category_id).first()
        if not category:
            return JSONResponse(
                status_code=400,
                content={"success": False, "message": "Categoria não encontrada"}
            )
        
        # Atualizar dados do produto
        product.name = name
        product.description = description
        product.price = price
        product.category_id = category_id
        product.image_url = image_url if image_url else None
        product.download_url = download_url if download_url else None
        product.duration_days = duration_days if price > 0 else None
        product.tags = tags
        product.requirements = requirements
        product.is_active = is_active
        product.updated_at = datetime.utcnow()
        
        db.commit()
        db.refresh(product)
        
        # Sincronizar automaticamente com Stripe se for produto pago
        stripe_result = None
        if price > 0:
            try:
                from stripe_product_sync import auto_sync_product_update
                stripe_result = auto_sync_product_update(product, db)
                if not stripe_result['success']:
                    logger.warning(f"Erro na sincronização Stripe: {stripe_result.get('error')}")
            except Exception as e:
                logger.warning(f"Erro na sincronização automática com Stripe: {e}")
        
        response_data = {
            "success": True,
            "message": "Produto atualizado com sucesso!",
            "product_id": product.id
        }
        
        # Adicionar informações do Stripe se sincronizado
        if stripe_result and stripe_result['success']:
            response_data["stripe_synced"] = True
            response_data["stripe_product_id"] = stripe_result.get('stripe_product_id')
        
        return JSONResponse(content=response_data)
        
    except Exception as e:
        logger.error(f"Erro ao atualizar produto: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "message": "Erro interno do servidor"}
        )

@app.post("/api/admin/categories")
async def api_create_category(
    request: Request,
    name: str = Form(...),
    description: str = Form(None),
    db: Session = Depends(get_db)
):
    """API para criar categoria (admin apenas)"""
    try:
        current_user = get_current_user_simple(request, db)
        if not current_user or not current_user.is_admin:
            return JSONResponse(
                status_code=403,
                content={"success": False, "message": "Acesso negado"}
            )
        
        # Verificar se categoria já existe
        existing = db.query(Category).filter(Category.name == name).first()
        if existing:
            return JSONResponse(
                status_code=400,
                content={"success": False, "message": "Categoria já existe"}
            )
        
        # Criar categoria
        new_category = Category(
            name=name,
            description=description,
            is_active=True
        )
        
        db.add(new_category)
        db.commit()
        
        return JSONResponse(content={
            "success": True,
            "message": "Categoria criada com sucesso!",
            "category_id": new_category.id
        })
        
    except Exception as e:
        logger.error(f"Erro ao criar categoria: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "message": "Erro interno do servidor"}
        )

@app.get("/api/admin/users")
async def api_get_users(request: Request, db: Session = Depends(get_db)):
    """API para obter lista de usuários (admin apenas)"""
    try:
        current_user = get_current_user_simple(request, db)
        if not current_user or not current_user.is_admin:
            return JSONResponse(
                status_code=403,
                content={"success": False, "message": "Acesso negado"}
            )
        
        # Buscar usuários com contagem de licenças
        users = db.query(User).all()
        users_data = []
        
        for user in users:
            license_count = db.query(License).filter(
                License.user_id == user.id,
                License.status == "active"
            ).count()
            
            users_data.append({
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "is_active": user.is_active,
                "is_admin": user.is_admin,
                "license_count": license_count,
                "created_at": user.created_at.strftime("%d/%m/%Y") if user.created_at else None
            })
        
        return JSONResponse(content={
            "success": True,
            "users": users_data
        })
        
    except Exception as e:
        logger.error(f"Erro ao buscar usuários: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "message": "Erro interno do servidor"}
        )

@app.get("/api/admin/licenses")
async def api_get_licenses(request: Request, db: Session = Depends(get_db)):
    """API para obter lista de licenças (admin apenas)"""
    try:
        current_user = get_current_user_simple(request, db)
        if not current_user or not current_user.is_admin:
            return JSONResponse(
                status_code=403,
                content={"success": False, "message": "Acesso negado"}
            )
        
        # Buscar licenças com dados do usuário e produto
        licenses = db.query(License).join(User).join(Product).all()
        licenses_data = []
        
        for license_obj in licenses:
            licenses_data.append({
                "license_key": license_obj.license_key,
                "user_username": license_obj.user.username,
                "product_name": license_obj.product.name,
                "is_active": license_obj.status == "active",
                "expires_at": license_obj.expires_at.strftime("%d/%m/%Y") if license_obj.expires_at else None,
                "created_at": license_obj.created_at.strftime("%d/%m/%Y") if license_obj.created_at else None
            })
        
        return JSONResponse(content={
            "success": True,
            "licenses": licenses_data
        })
        
    except Exception as e:
        logger.error(f"Erro ao buscar licenças: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "message": "Erro interno do servidor"}
        )

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

@app.post("/api/admin/product")
async def api_create_product(
    request: Request,
    name: str = Form(...),
    description: str = Form(...),
    image_url: str = Form(None),
    category_id: int = Form(None),
    pricing_type: str = Form(...),
    download_url: str = Form(None),
    price: float = Form(None),
    duration_days: int = Form(30),
    paid_download_url: str = Form(None),
    tags: str = Form(None),
    requirements: str = Form(None),
    db: Session = Depends(get_db)
):
    """API para criar produto (admin apenas)"""
    try:
        current_user = get_current_user_simple(request, db)
        if not current_user or not current_user.is_admin:
            return JSONResponse(
                status_code=403,
                content={"success": False, "message": "Acesso negado"}
            )
        
        # Validações
        if pricing_type == "free" and not download_url:
            return JSONResponse(
                status_code=400,
                content={"success": False, "message": "Link de download é obrigatório para produtos gratuitos"}
            )
        
        if pricing_type == "paid" and (not price or price <= 0):
            return JSONResponse(
                status_code=400,
                content={"success": False, "message": "Preço é obrigatório para produtos pagos"}
            )
        
        # Criar produto
        product_data = {
            "name": name,
            "description": description,
            "image_url": image_url,
            "category_id": category_id,
            "price": 0.0 if pricing_type == "free" else price,
            "duration_days": duration_days if pricing_type == "paid" else None,
            "download_url": download_url if pricing_type == "free" else paid_download_url,
            "tags": tags,
            "requirements": requirements,
            "is_active": True,
            "is_featured": False
        }
        
        new_product = Product(**product_data)
        db.add(new_product)
        db.commit()
        db.refresh(new_product)
        
        return JSONResponse(content={
            "success": True, 
            "message": "Produto criado com sucesso",
            "product_id": new_product.id
        })
        
    except Exception as e:
        logger.error(f"Erro ao criar produto: {e}")
        db.rollback()
        return JSONResponse(
            status_code=500,
            content={"success": False, "message": "Erro interno do servidor"}
        )

@app.delete("/api/admin/product/{product_id}")
async def api_delete_product(
    request: Request,
    product_id: int,
    db: Session = Depends(get_db)
):
    """API para deletar produto (admin apenas)"""
    try:
        current_user = get_current_user_simple(request, db)
        if not current_user or not current_user.is_admin:
            return JSONResponse(
                status_code=403,
                content={"success": False, "message": "Acesso negado"}
            )
        
        product = db.query(Product).filter(Product.id == product_id).first()
        if not product:
            return JSONResponse(
                status_code=404,
                content={"success": False, "message": "Produto não encontrado"}
            )
        
        # Verificar se há licenças ativas
        active_licenses = db.query(License).filter(
            License.product_id == product_id,
            License.is_active == True
        ).count()
        
        if active_licenses > 0:
            # Desativar ao invés de deletar se há licenças ativas
            product.is_active = False
            db.commit()
            return JSONResponse(content={
                "success": True, 
                "message": "Produto desativado (há licenças ativas)"
            })
        else:
            # Deletar produto
            db.delete(product)
            db.commit()
            return JSONResponse(content={
                "success": True, 
                "message": "Produto excluído com sucesso"
            })
        
    except Exception as e:
        logger.error(f"Erro ao deletar produto: {e}")
        db.rollback()
        return JSONResponse(
            status_code=500,
            content={"success": False, "message": "Erro interno do servidor"}
        )

@app.post("/api/change-password")
async def api_change_password(request: Request, db: Session = Depends(get_db)):
    """API para alterar senha do usuário"""
    try:
        current_user = get_current_user_simple(request, db)
        if not current_user:
            return JSONResponse(
                status_code=401,
                content={"success": False, "message": "Login necessário"}
            )
        
        # Obter dados do request JSON
        body = await request.json()
        current_password = body.get("current_password")
        new_password = body.get("new_password")
        
        if not current_password or not new_password:
            return JSONResponse(
                status_code=400,
                content={"success": False, "message": "Senha atual e nova senha são obrigatórias"}
            )
        
        # Verificar senha atual
        if not verify_password(current_password, current_user.senha_hash):
            return JSONResponse(
                status_code=400,
                content={"success": False, "message": "Senha atual incorreta"}
            )
        
        # Validar nova senha
        if len(new_password) < 6:
            return JSONResponse(
                status_code=400,
                content={"success": False, "message": "A nova senha deve ter pelo menos 6 caracteres"}
            )
        
        # Atualizar senha
        current_user.senha_hash = hash_password(new_password)
        db.commit()
        
        return JSONResponse(content={
            "success": True,
            "message": "Senha alterada com sucesso!"
        })
        
    except Exception as e:
        logger.error(f"Erro ao alterar senha: {e}")
        db.rollback()
        return JSONResponse(
            status_code=500,
            content={"success": False, "message": "Erro interno do servidor"}
        )

@app.get("/health")
async def health_check():
    """Health check da aplicação"""
    return {"status": "ok", "message": "FovDark está funcionando"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)