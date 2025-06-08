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
from infinite_pay_simple import create_payment_link
from security import add_security_headers, validate_input, log_security_event
from stripe_integration import create_checkout_session, handle_successful_payment, verify_webhook_signature, process_webhook_event

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
        from stripe_simple import get_user_active_licenses
        
        # Obter licenças ativas do usuário (produtos pagos)
        user_licenses = get_user_active_licenses(db, current_user.id)
        
        # Obter produtos gratuitos disponíveis
        free_products = db.query(Product).filter(
            Product.is_active == True,
            Product.price == 0,
            Product.download_url.isnot(None)
        ).all()
        
        return templates.TemplateResponse("downloads.html", {
            "request": request,
            "user": current_user,
            "licenses": user_licenses,
            "free_products": free_products
        })
        
    except Exception as e:
        logger.error(f"Erro na página de downloads: {e}")
        return templates.TemplateResponse("downloads.html", {
            "request": request,
            "user": current_user,
            "user_licenses": [],
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
        
        # Criar link de pagamento no Infinite Pay
        payment_data = create_payment_link(
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
            payment_id=payment_data.get("reference"),
            status="pending"
        )
        
        db.add(transaction)
        db.commit()
        
        return JSONResponse({
            "success": True,
            "payment_url": payment_data.get("payment_url"),
            "reference": payment_data.get("reference")
        })
        
    except Exception as e:
        logger.error(f"Erro na compra do produto {product_id}: {e}")
        return JSONResponse({
            "success": False,
            "message": "Erro interno do servidor"
        }, status_code=500)

@app.post("/api/stripe/checkout/{product_id}")
@limiter.limit("5/minute")
async def stripe_checkout_product(
    request: Request,
    product_id: int,
    current_user: User = Depends(get_current_user),
    db=Depends(get_db)
):
    """API para checkout com Stripe"""
    try:
        from stripe_simple import create_stripe_checkout_session
        
        checkout_result = create_stripe_checkout_session(current_user.id, product_id, db)
        
        if checkout_result["success"]:
            return JSONResponse({
                "success": True,
                "checkout_url": checkout_result["checkout_url"],
                "session_id": checkout_result["session_id"],
                "amount": checkout_result["amount"],
                "product_name": checkout_result["product_name"],
                "duration_days": checkout_result["duration_days"]
            })
        else:
            return JSONResponse({
                "success": False,
                "message": checkout_result.get("error", "Erro ao criar checkout")
            }, status_code=400)
        
    except Exception as e:
        logger.error(f"Erro no checkout Stripe para produto {product_id}: {e}")
        return JSONResponse({
            "success": False,
            "message": "Erro interno do servidor"
        }, status_code=500)

@app.post("/api/webhook/stripe")
@limiter.limit("100/minute")
async def stripe_webhook(request: Request, db=Depends(get_db)):
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
        return JSONResponse({"error": "Erro interno"}, status_code=500)

@app.post("/api/webhook/infinite-pay")
@limiter.limit("100/minute")
async def infinite_pay_webhook(request: Request, db=Depends(get_db)):
    """Webhook do Infinite Pay para confirmação de pagamentos"""
    try:
        payload = await request.json()
        
        # Processar webhook (implementação simplificada)
        # Em produção, verificar assinatura do webhook
        
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

@app.get("/payment/success")
async def payment_success(request: Request, ref: str = None, session_id: str = None, db=Depends(get_db)):
    """Página de sucesso do pagamento"""
    try:
        license_data = None
        
        # Se é um pagamento do Stripe
        if session_id:
            try:
                license_data = handle_successful_payment(session_id, db)
            except Exception as e:
                logger.error(f"Erro ao processar pagamento Stripe: {e}")
        
        # Se é um pagamento do Infinite Pay
        elif ref:
            transaction = db.query(Transaction).filter(Transaction.payment_id == ref).first()
            if transaction:
                transaction.status = "approved"
                
                product = db.query(Product).filter(Product.id == transaction.product_id).first()
                if product:
                    license_obj = create_license(
                        db=db,
                        user_id=transaction.user_id,
                        product_id=product.id,
                        duration_days=product.duration_days or 30
                    )
                    
                    user = db.query(User).filter(User.id == transaction.user_id).first()
                    if user:
                        send_license_email(user.email, license_obj, product)
                
                db.commit()
        
        return templates.TemplateResponse("payment_success.html", {
            "request": request,
            "reference": ref,
            "session_id": session_id,
            "license_data": license_data
        })
        
    except Exception as e:
        logger.error(f"Erro na página de sucesso: {e}")
        return templates.TemplateResponse("payment_success.html", {
            "request": request,
            "error": "Erro ao processar pagamento"
        })

@app.get("/payment/cancel")
async def payment_cancel(request: Request, ref: str = None, db=Depends(get_db)):
    """Página de cancelamento do pagamento"""
    try:
        if ref:
            # Atualizar status da transação
            transaction = db.query(Transaction).filter(Transaction.payment_id == ref).first()
            if transaction:
                transaction.status = "cancelled"
                db.commit()
        
        return templates.TemplateResponse("payment_cancel.html", {
            "request": request,
            "reference": ref
        })
        
    except Exception as e:
        logger.error(f"Erro na página de cancelamento: {e}")
        return templates.TemplateResponse("payment_cancel.html", {
            "request": request,
            "error": "Erro ao processar cancelamento"
        })

@app.get("/payment/pending")
async def payment_pending(request: Request, ref: str = None):
    """Página de pagamento pendente"""
    return templates.TemplateResponse("payment_pending.html", {
        "request": request,
        "reference": ref
    })

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

@app.get("/api/download/{product_id}")
@limiter.limit("10/minute")
async def api_download_product(
    request: Request,
    product_id: int,
    current_user: User = Depends(get_current_user),
    db=Depends(get_db)
):
    """API para fazer download de produto (gratuito com login, pago com licença)"""
    try:
        # Buscar produto
        product = db.query(Product).filter(Product.id == product_id).first()
        if not product or not product.download_url:
            return JSONResponse({
                "success": False,
                "message": "Produto ou link de download não encontrado"
            }, status_code=404)
        
        # Se produto é gratuito, apenas verificar login
        if product.is_free:
            # Registrar download gratuito
            download_record = Download(
                user_id=current_user.id,
                product_id=product_id,
                license_id=None,  # Produtos gratuitos não precisam de licença
                ip_address=request.client.host if request.client else "unknown",
                user_agent=request.headers.get("user-agent", "")
            )
            db.add(download_record)
            
            # Incrementar contador de downloads
            db.query(Product).filter(Product.id == product_id).update({
                'download_count': Product.download_count + 1
            })
            db.commit()
            
            return JSONResponse({
                "success": True,
                "download_url": product.download_url,
                "product_name": product.name,
                "is_free": True,
                "message": "Download gratuito liberado"
            })
        
        # Se produto é pago, verificar licença ativa
        from stripe_simple import check_user_license
        license_check = check_user_license(db, current_user.id, product_id)
        
        if not license_check.get('has_license', False):
            return JSONResponse({
                "success": False,
                "message": "Você precisa comprar uma licença para fazer download deste produto pago",
                "requires_purchase": True,
                "product_price": float(product.price)
            }, status_code=403)
        
        # Buscar a licença para registrar o download
        license_obj = db.query(License).filter(
            License.user_id == current_user.id,
            License.product_id == product_id,
            License.status == 'active',
            License.expires_at > datetime.utcnow()
        ).first()
        
        if license_obj:
            # Registrar download licenciado
            download_record = Download(
                user_id=current_user.id,
                product_id=product_id,
                license_id=license_obj.id,
                ip_address=request.client.host if request.client else "unknown",
                user_agent=request.headers.get("user-agent", "")
            )
            db.add(download_record)
            db.commit()
        
        # Retornar informações do download
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

# Rotas de API Admin para gerenciamento de produtos
@app.get("/admin/api/products/{product_id}")
@limiter.limit("30/minute")
async def api_get_product(
    request: Request,
    product_id: int,
    current_user: User = Depends(get_current_user),
    db=Depends(get_db)
):
    """API para obter detalhes do produto (admin apenas)"""
    try:
        # Verificar se é admin
        if not current_user.is_admin:
            raise HTTPException(status_code=403, detail="Acesso negado")
        
        product = db.query(Product).filter(Product.id == product_id).first()
        if not product:
            raise HTTPException(status_code=404, detail="Produto não encontrado")
        
        return {
            "id": product.id,
            "name": product.name,
            "description": product.description,
            "price": float(product.price),
            "category_id": product.category_id,
            "duration_days": product.duration_days,
            "download_url": product.download_url,
            "requirements": product.requirements,
            "tags": product.tags,
            "is_featured": product.is_featured,
            "is_active": product.is_active,
            "download_count": product.download_count,
            "created_at": product.created_at.isoformat() if product.created_at else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao obter produto {product_id}: {e}")
        raise HTTPException(status_code=500, detail="Erro interno do servidor")

@app.put("/admin/api/products/{product_id}")
@limiter.limit("10/minute")
async def api_update_product(
    request: Request,
    product_id: int,
    name: str = Form(...),
    description: str = Form(...),
    price: float = Form(...),
    category_id: int = Form(...),
    duration_days: int = Form(30),
    download_url: str = Form(None),
    requirements: str = Form(None),
    tags: str = Form(None),
    is_featured: bool = Form(False),
    image: UploadFile = File(None),
    current_user: User = Depends(get_current_user),
    db=Depends(get_db)
):
    """API para atualizar produto (admin apenas)"""
    try:
        # Verificar se é admin
        if not current_user.is_admin:
            raise HTTPException(status_code=403, detail="Acesso negado")
        
        # Buscar produto
        product = db.query(Product).filter(Product.id == product_id).first()
        if not product:
            raise HTTPException(status_code=404, detail="Produto não encontrado")
        
        # Validar dados
        if price < 0:
            raise HTTPException(status_code=400, detail="Preço deve ser positivo")
        
        if duration_days < 1:
            raise HTTPException(status_code=400, detail="Duração deve ser pelo menos 1 dia")
        
        # Verificar se categoria existe
        category = db.query(Category).filter(Category.id == category_id).first()
        if not category:
            raise HTTPException(status_code=400, detail="Categoria não encontrada")
        
        # Atualizar dados do produto
        product.name = name.strip()
        product.description = description.strip() if description else None
        product.price = price
        product.category_id = category_id
        product.duration_days = duration_days
        product.download_url = download_url.strip() if download_url else None
        product.requirements = requirements.strip() if requirements else None
        product.tags = tags.strip() if tags else None
        product.is_featured = is_featured
        product.updated_at = datetime.utcnow()
        
        # Processar imagem se fornecida
        if image and image.filename:
            # Validar tipo de arquivo
            allowed_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}
            file_extension = os.path.splitext(image.filename)[1].lower()
            
            if file_extension not in allowed_extensions:
                raise HTTPException(status_code=400, detail="Tipo de imagem não permitido")
            
            # Salvar imagem
            image_filename = f"product_{product_id}_{uuid.uuid4().hex}{file_extension}"
            image_path = f"static/uploads/{image_filename}"
            
            with open(image_path, "wb") as buffer:
                shutil.copyfileobj(image.file, buffer)
            
            # Remover imagem antiga se existir
            if product.image_url:
                old_image_path = f"static/uploads/{os.path.basename(product.image_url)}"
                if os.path.exists(old_image_path):
                    os.remove(old_image_path)
            
            product.image_url = f"/uploads/{image_filename}"
        
        db.commit()
        
        return {
            "success": True,
            "message": "Produto atualizado com sucesso",
            "product": {
                "id": product.id,
                "name": product.name,
                "price": float(product.price)
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao atualizar produto {product_id}: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Erro interno do servidor")

@app.delete("/admin/api/products/{product_id}")
@limiter.limit("10/minute")
async def api_delete_product(
    request: Request,
    product_id: int,
    current_user: User = Depends(get_current_user),
    db=Depends(get_db)
):
    """API para deletar produto (admin apenas)"""
    try:
        # Verificar se é admin
        if not current_user.is_admin:
            raise HTTPException(status_code=403, detail="Acesso negado")
        
        # Buscar produto
        product = db.query(Product).filter(Product.id == product_id).first()
        if not product:
            raise HTTPException(status_code=404, detail="Produto não encontrado")
        
        # Verificar se existem licenças ativas para este produto
        active_licenses = db.query(License).filter(
            License.product_id == product_id,
            License.status == 'active'
        ).count()
        
        if active_licenses > 0:
            raise HTTPException(
                status_code=400, 
                detail=f"Não é possível deletar produto com {active_licenses} licenças ativas"
            )
        
        # Remover imagem se existir
        if product.image_url:
            image_path = f"static/uploads/{os.path.basename(product.image_url)}"
            if os.path.exists(image_path):
                os.remove(image_path)
        
        # Deletar produto
        db.delete(product)
        db.commit()
        
        return {
            "success": True,
            "message": "Produto deletado com sucesso"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao deletar produto {product_id}: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Erro interno do servidor")

@app.get("/admin/api/users/{user_id}")
@limiter.limit("30/minute")
async def api_get_user(
    request: Request,
    user_id: int,
    current_user: User = Depends(get_current_user),
    db=Depends(get_db)
):
    """API para obter detalhes do usuário (admin apenas)"""
    try:
        # Verificar se é admin
        if not current_user.is_admin:
            raise HTTPException(status_code=403, detail="Acesso negado")
        
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="Usuário não encontrado")
        
        # Buscar licenças ativas
        active_licenses = db.query(License).filter(
            License.user_id == user_id,
            License.status == 'active'
        ).count()
        
        # Buscar total de compras
        total_purchases = db.query(Transaction).filter(
            Transaction.user_id == user_id,
            Transaction.status == 'approved'
        ).count()
        
        return {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "is_active": user.is_active,
            "is_admin": user.is_admin,
            "active_licenses_count": active_licenses,
            "total_purchases": total_purchases,
            "last_login": user.last_login.isoformat() if user.last_login else None,
            "created_at": user.created_at.strftime('%d/%m/%Y %H:%M') if user.created_at else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao obter usuário {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Erro interno do servidor")

@app.put("/admin/api/users/{user_id}/status")
@limiter.limit("10/minute")
async def api_update_user_status(
    request: Request,
    user_id: int,
    current_user: User = Depends(get_current_user),
    db=Depends(get_db)
):
    """API para atualizar status do usuário (admin apenas)"""
    try:
        # Verificar se é admin
        if not current_user.is_admin:
            raise HTTPException(status_code=403, detail="Acesso negado")
        
        # Obter dados do corpo da requisição
        body = await request.json()
        is_active = body.get("is_active")
        
        if is_active is None:
            raise HTTPException(status_code=400, detail="Status is_active é obrigatório")
        
        # Buscar usuário
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="Usuário não encontrado")
        
        # Não permitir desativar próprio usuário admin
        if user.id == current_user.id and user.is_admin and not is_active:
            raise HTTPException(status_code=400, detail="Não é possível desativar sua própria conta admin")
        
        # Atualizar status
        user.is_active = is_active
        db.commit()
        
        return {
            "success": True,
            "message": f"Usuário {'ativado' if is_active else 'desativado'} com sucesso"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao atualizar status do usuário {user_id}: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Erro interno do servidor")

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
