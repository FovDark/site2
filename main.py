import os
import uvicorn
from fastapi import FastAPI, Request, Depends, HTTPException, status, Form, File, UploadFile
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
import logging
from datetime import datetime, timedelta
import json
import hashlib
import platform
import subprocess
import uuid
from typing import Optional, List
import shutil

from database import get_db, create_tables
from models import User, Product, License, Transaction, Category, Download
from auth import authenticate_user, create_access_token, get_current_user, hash_password, verify_password
from admin import get_admin_stats, create_product, update_product, delete_product
from license import verify_license, create_license, get_hwid
from email_utils import send_password_reset_email, send_license_email
from password_recovery import create_reset_token, verify_reset_token
from infinite_pay import create_payment, verify_payment_webhook
from security import add_security_headers, validate_input, log_security_event

# Configuração de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Rate limiting
limiter = Limiter(key_func=get_remote_address)
app = FastAPI(title="FovDark - Sistema de Licenças Digitais", version="1.0.0")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.getenv("ALLOWED_ORIGINS", "*").split(",")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Trusted host middleware
app.add_middleware(
    TrustedHostMiddleware, 
    allowed_hosts=[os.getenv("ALLOWED_HOSTS", "*").split(",")]
)

# Templates e arquivos estáticos
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/uploads", StaticFiles(directory="static/uploads"), name="uploads")

# Criar diretórios necessários
os.makedirs("static/uploads", exist_ok=True)
os.makedirs("static/downloads", exist_ok=True)

# Middleware para headers de segurança
@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    return add_security_headers(response)

# Eventos de inicialização
@app.on_event("startup")
async def startup_event():
    await create_tables()
    logger.info("FovDark iniciado com sucesso!")

# Rotas principais
@app.get("/", response_class=HTMLResponse)
@limiter.limit("30/minute")
async def index(request: Request, db=Depends(get_db)):
    """Página inicial com produtos em destaque"""
    try:
        # Buscar produtos em destaque
        featured_products = db.query(Product).filter(Product.is_featured == True).limit(6).all()
        categories = db.query(Category).all()
        
        return templates.TemplateResponse("index.html", {
            "request": request,
            "products": featured_products,
            "categories": categories
        })
    except Exception as e:
        logger.error(f"Erro na página inicial: {e}")
        return templates.TemplateResponse("index.html", {
            "request": request,
            "products": [],
            "categories": [],
            "error": "Erro ao carregar produtos"
        })

@app.get("/login", response_class=HTMLResponse)
@limiter.limit("10/minute")
async def login_page(request: Request):
    """Página de login"""
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/login")
@limiter.limit("5/minute")
async def login(request: Request, username: str = Form(...), password: str = Form(...), db=Depends(get_db)):
    """Processar login do usuário"""
    try:
        # Validar entrada
        username = validate_input(username, "username")
        password = validate_input(password, "password")
        
        # Autenticar usuário
        user = authenticate_user(db, username, password)
        if not user:
            log_security_event("failed_login", {"username": username, "ip": get_remote_address(request)})
            return templates.TemplateResponse("login.html", {
                "request": request,
                "error": "Usuário ou senha inválidos"
            })
        
        # Criar token de acesso
        access_token = create_access_token(data={"sub": user.username})
        
        # Log de login bem-sucedido
        log_security_event("successful_login", {"username": username, "ip": get_remote_address(request)})
        
        # Redirecionar para painel ou admin
        redirect_url = "/admin" if user.is_admin else "/painel"
        response = RedirectResponse(url=redirect_url, status_code=302)
        response.set_cookie(
            key="access_token",
            value=f"Bearer {access_token}",
            httponly=True,
            secure=True,
            samesite="strict"
        )
        return response
        
    except Exception as e:
        logger.error(f"Erro no login: {e}")
        return templates.TemplateResponse("login.html", {
            "request": request,
            "error": "Erro interno do servidor"
        })

@app.get("/register", response_class=HTMLResponse)
@limiter.limit("10/minute")
async def register_page(request: Request):
    """Página de registro"""
    return templates.TemplateResponse("register.html", {"request": request})

@app.post("/register")
@limiter.limit("3/minute")
async def register(
    request: Request,
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    confirm_password: str = Form(...),
    db=Depends(get_db)
):
    """Registrar novo usuário"""
    try:
        # Validar entrada
        username = validate_input(username, "username")
        email = validate_input(email, "email")
        password = validate_input(password, "password")
        
        # Validar senhas
        if password != confirm_password:
            return templates.TemplateResponse("register.html", {
                "request": request,
                "error": "As senhas não coincidem"
            })
        
        # Verificar se usuário já existe
        existing_user = db.query(User).filter(
            (User.username == username) | (User.email == email)
        ).first()
        
        if existing_user:
            return templates.TemplateResponse("register.html", {
                "request": request,
                "error": "Usuário ou email já existe"
            })
        
        # Criar novo usuário
        hashed_password = hash_password(password)
        new_user = User(
            username=username,
            email=email,
            password_hash=hashed_password,
            is_active=True,
            is_admin=False
        )
        
        db.add(new_user)
        db.commit()
        
        log_security_event("user_registered", {"username": username, "email": email})
        
        return templates.TemplateResponse("login.html", {
            "request": request,
            "success": "Usuário registrado com sucesso! Faça login para continuar."
        })
        
    except Exception as e:
        logger.error(f"Erro no registro: {e}")
        return templates.TemplateResponse("register.html", {
            "request": request,
            "error": "Erro interno do servidor"
        })

@app.get("/painel", response_class=HTMLResponse)
@limiter.limit("20/minute")
async def painel(request: Request, current_user: User = Depends(get_current_user), db=Depends(get_db)):
    """Painel do usuário"""
    try:
        # Buscar licenças do usuário
        licenses = db.query(License).filter(License.user_id == current_user.id).all()
        
        # Buscar transações do usuário
        transactions = db.query(Transaction).filter(Transaction.user_id == current_user.id).order_by(Transaction.created_at.desc()).limit(10).all()
        
        # Buscar downloads do usuário
        downloads = db.query(Download).filter(Download.user_id == current_user.id).order_by(Download.downloaded_at.desc()).limit(10).all()
        
        return templates.TemplateResponse("painel.html", {
            "request": request,
            "user": current_user,
            "licenses": licenses,
            "transactions": transactions,
            "downloads": downloads
        })
        
    except Exception as e:
        logger.error(f"Erro no painel: {e}")
        return templates.TemplateResponse("painel.html", {
            "request": request,
            "user": current_user,
            "licenses": [],
            "transactions": [],
            "downloads": [],
            "error": "Erro ao carregar dados do painel"
        })

@app.get("/admin", response_class=HTMLResponse)
@limiter.limit("20/minute")
async def admin_panel(request: Request, current_user: User = Depends(get_current_user), db=Depends(get_db)):
    """Painel administrativo"""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Acesso negado")
    
    try:
        stats = get_admin_stats(db)
        products = db.query(Product).all()
        users = db.query(User).order_by(User.created_at.desc()).limit(20).all()
        transactions = db.query(Transaction).order_by(Transaction.created_at.desc()).limit(20).all()
        categories = db.query(Category).all()
        
        return templates.TemplateResponse("admin.html", {
            "request": request,
            "user": current_user,
            "stats": stats,
            "products": products,
            "users": users,
            "transactions": transactions,
            "categories": categories
        })
        
    except Exception as e:
        logger.error(f"Erro no painel admin: {e}")
        return templates.TemplateResponse("admin.html", {
            "request": request,
            "user": current_user,
            "error": "Erro ao carregar dados administrativos"
        })

@app.get("/products/{product_id}", response_class=HTMLResponse)
@limiter.limit("30/minute")
async def product_detail(request: Request, product_id: int, db=Depends(get_db)):
    """Página de detalhes do produto"""
    try:
        product = db.query(Product).filter(Product.id == product_id).first()
        if not product:
            raise HTTPException(status_code=404, detail="Produto não encontrado")
        
        # Produtos relacionados da mesma categoria
        related_products = db.query(Product).filter(
            Product.category_id == product.category_id,
            Product.id != product_id
        ).limit(4).all()
        
        return templates.TemplateResponse("product.html", {
            "request": request,
            "product": product,
            "related_products": related_products
        })
        
    except Exception as e:
        logger.error(f"Erro ao carregar produto {product_id}: {e}")
        raise HTTPException(status_code=404, detail="Produto não encontrado")

@app.get("/downloads", response_class=HTMLResponse)
@limiter.limit("20/minute")
async def downloads_page(request: Request, current_user: User = Depends(get_current_user), db=Depends(get_db)):
    """Página de downloads do usuário"""
    try:
        # Buscar licenças ativas do usuário
        active_licenses = db.query(License).filter(
            License.user_id == current_user.id,
            License.status == "active",
            License.expires_at > datetime.utcnow()
        ).all()
        
        # Buscar produtos disponíveis para download
        available_products = []
        for license_obj in active_licenses:
            product = db.query(Product).filter(Product.id == license_obj.product_id).first()
            if product and product.download_url:
                available_products.append({
                    "product": product,
                    "license": license_obj
                })
        
        return templates.TemplateResponse("downloads.html", {
            "request": request,
            "user": current_user,
            "available_products": available_products
        })
        
    except Exception as e:
        logger.error(f"Erro na página de downloads: {e}")
        return templates.TemplateResponse("downloads.html", {
            "request": request,
            "user": current_user,
            "available_products": [],
            "error": "Erro ao carregar downloads"
        })

# API Routes
@app.post("/api/products")
@limiter.limit("10/minute")
async def api_create_product(
    request: Request,
    name: str = Form(...),
    description: str = Form(...),
    price: float = Form(...),
    category_id: int = Form(...),
    duration_days: int = Form(30),
    download_url: str = Form(None),
    requirements: str = Form(None),
    tags: str = Form(None),
    image: UploadFile = File(None),
    current_user: User = Depends(get_current_user),
    db=Depends(get_db)
):
    """API para criar produto (admin apenas)"""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Acesso negado")
    
    try:
        # Upload de imagem se fornecida
        image_url = None
        if image and image.filename:
            file_extension = image.filename.split(".")[-1].lower()
            if file_extension in ["jpg", "jpeg", "png", "gif", "webp"]:
                filename = f"{uuid.uuid4()}.{file_extension}"
                file_path = f"static/uploads/{filename}"
                
                with open(file_path, "wb") as buffer:
                    shutil.copyfileobj(image.file, buffer)
                
                image_url = f"/uploads/{filename}"
        
        # Criar produto
        product_data = {
            "name": name,
            "description": description,
            "price": price,
            "category_id": category_id,
            "duration_days": duration_days,
            "download_url": download_url,
            "requirements": requirements,
            "tags": tags,
            "image_url": image_url
        }
        
        product = create_product(db, product_data)
        
        return JSONResponse({
            "success": True,
            "message": "Produto criado com sucesso",
            "product_id": product.id
        })
        
    except Exception as e:
        logger.error(f"Erro ao criar produto: {e}")
        return JSONResponse({
            "success": False,
            "message": "Erro ao criar produto"
        }, status_code=500)

@app.post("/api/purchase/{product_id}")
@limiter.limit("5/minute")
async def api_purchase_product(
    request: Request,
    product_id: int,
    current_user: User = Depends(get_current_user),
    db=Depends(get_db)
):
    """API para comprar produto"""
    try:
        product = db.query(Product).filter(Product.id == product_id).first()
        if not product:
            return JSONResponse({
                "success": False,
                "message": "Produto não encontrado"
            }, status_code=404)
        
        # Criar pagamento no Infinite Pay
        payment_data = create_payment(
            amount=product.price,
            description=f"Licença {product.name}",
            user_id=current_user.id,
            product_id=product_id
        )
        
        if not payment_data.get("success"):
            return JSONResponse({
                "success": False,
                "message": "Erro ao criar pagamento"
            }, status_code=500)
        
        # Salvar transação
        transaction = Transaction(
            user_id=current_user.id,
            product_id=product_id,
            amount=product.price,
            payment_id=payment_data.get("payment_id"),
            status="pending"
        )
        
        db.add(transaction)
        db.commit()
        
        return JSONResponse({
            "success": True,
            "payment_url": payment_data.get("payment_url"),
            "payment_id": payment_data.get("payment_id")
        })
        
    except Exception as e:
        logger.error(f"Erro na compra do produto {product_id}: {e}")
        return JSONResponse({
            "success": False,
            "message": "Erro interno do servidor"
        }, status_code=500)

@app.post("/api/webhook/infinite-pay")
@limiter.limit("100/minute")
async def infinite_pay_webhook(request: Request, db=Depends(get_db)):
    """Webhook do Infinite Pay para confirmação de pagamentos"""
    try:
        payload = await request.json()
        
        # Verificar webhook
        is_valid = verify_payment_webhook(payload)
        if not is_valid:
            return JSONResponse({"error": "Webhook inválido"}, status_code=400)
        
        payment_id = payload.get("payment_id")
        status = payload.get("status")
        
        # Buscar transação
        transaction = db.query(Transaction).filter(Transaction.payment_id == payment_id).first()
        if not transaction:
            return JSONResponse({"error": "Transação não encontrada"}, status_code=404)
        
        # Atualizar status da transação
        transaction.status = status
        
        # Se pagamento aprovado, criar licença
        if status == "approved":
            product = db.query(Product).filter(Product.id == transaction.product_id).first()
            if product:
                license_obj = create_license(
                    db=db,
                    user_id=transaction.user_id,
                    product_id=product.id,
                    duration_days=product.duration_days
                )
                
                # Enviar email com licença
                user = db.query(User).filter(User.id == transaction.user_id).first()
                if user:
                    send_license_email(user.email, license_obj, product)
        
        db.commit()
        
        return JSONResponse({"status": "ok"})
        
    except Exception as e:
        logger.error(f"Erro no webhook Infinite Pay: {e}")
        return JSONResponse({"error": "Erro interno"}, status_code=500)

@app.get("/api/verify-license/{license_key}")
@limiter.limit("60/minute")
async def api_verify_license(request: Request, license_key: str, hwid: str = None, db=Depends(get_db)):
    """API para verificar licença"""
    try:
        # Se HWID não fornecido, tentar obter automaticamente
        if not hwid:
            hwid = get_hwid()
        
        # Verificar licença
        is_valid, license_obj = verify_license(db, license_key, hwid)
        
        if is_valid:
            return JSONResponse({
                "valid": True,
                "license": {
                    "id": license_obj.id,
                    "status": license_obj.status,
                    "expires_at": license_obj.expires_at.isoformat(),
                    "product_name": license_obj.product.name
                }
            })
        else:
            return JSONResponse({
                "valid": False,
                "message": "Licença inválida ou expirada"
            })
            
    except Exception as e:
        logger.error(f"Erro na verificação de licença: {e}")
        return JSONResponse({
            "valid": False,
            "message": "Erro interno do servidor"
        }, status_code=500)

@app.post("/api/download/{product_id}")
@limiter.limit("10/minute")
async def api_download_product(
    request: Request,
    product_id: int,
    current_user: User = Depends(get_current_user),
    db=Depends(get_db)
):
    """API para fazer download de produto"""
    try:
        # Verificar se usuário tem licença ativa para o produto
        license_obj = db.query(License).filter(
            License.user_id == current_user.id,
            License.product_id == product_id,
            License.status == "active",
            License.expires_at > datetime.utcnow()
        ).first()
        
        if not license_obj:
            return JSONResponse({
                "success": False,
                "message": "Licença não encontrada ou expirada"
            }, status_code=403)
        
        product = db.query(Product).filter(Product.id == product_id).first()
        if not product or not product.download_url:
            return JSONResponse({
                "success": False,
                "message": "Download não disponível"
            }, status_code=404)
        
        # Registrar download
        download = Download(
            user_id=current_user.id,
            product_id=product_id,
            license_id=license_obj.id
        )
        
        db.add(download)
        db.commit()
        
        return JSONResponse({
            "success": True,
            "download_url": product.download_url
        })
        
    except Exception as e:
        logger.error(f"Erro no download do produto {product_id}: {e}")
        return JSONResponse({
            "success": False,
            "message": "Erro interno do servidor"
        }, status_code=500)

@app.post("/api/forgot-password")
@limiter.limit("3/minute")
async def api_forgot_password(request: Request, email: str = Form(...), db=Depends(get_db)):
    """API para recuperação de senha"""
    try:
        user = db.query(User).filter(User.email == email).first()
        if user:
            reset_token = create_reset_token(user.id)
            send_password_reset_email(email, reset_token)
        
        # Sempre retornar sucesso por segurança
        return JSONResponse({
            "success": True,
            "message": "Se o email existir, um link de recuperação será enviado"
        })
        
    except Exception as e:
        logger.error(f"Erro na recuperação de senha: {e}")
        return JSONResponse({
            "success": False,
            "message": "Erro interno do servidor"
        }, status_code=500)

@app.get("/logout")
async def logout():
    """Logout do usuário"""
    response = RedirectResponse(url="/", status_code=302)
    response.delete_cookie("access_token")
    return response

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=5000,
        reload=True,
        log_level="info"
    )
