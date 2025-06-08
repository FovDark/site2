from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text, ForeignKey, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime, timedelta
import uuid

Base = declarative_base()

class User(Base):
    """Modelo de usuário compatível com Supabase"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    senha_hash = Column(String(255), nullable=False)
    data_expiracao = Column(DateTime, nullable=True)
    is_admin = Column(Boolean, nullable=True, default=False)
    created_at = Column(DateTime, nullable=True, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=True, default=datetime.utcnow, onupdate=datetime.utcnow)
    hwid = Column(Text, nullable=True)
    status_licenca = Column(String(50), nullable=True, default='pendente')
    tentativas_login = Column(Integer, nullable=True, default=0)
    ultimo_login = Column(DateTime, nullable=True)
    ip_registro = Column(String(45), nullable=True)
    ip_ultimo_login = Column(String(45), nullable=True)
    
    # Relacionamentos
    licenses = relationship("License", back_populates="user")
    transactions = relationship("Transaction", back_populates="user")
    downloads = relationship("Download", back_populates="user")
    
    def __repr__(self):
        return f"<User(email='{self.email}', status='{self.status_licenca}')>"
    
    # Propriedades para compatibilidade com código existente
    @property
    def username(self):
        return self.email.split('@')[0] if self.email else None
    
    @property
    def password_hash(self):
        return self.senha_hash
    
    @password_hash.setter
    def password_hash(self, value):
        self.senha_hash = value
    
    @property
    def is_active(self):
        return self.status_licenca != 'suspenso'
    
    @property
    def last_login(self):
        return self.ultimo_login
    
    @last_login.setter
    def last_login(self, value):
        self.ultimo_login = value

class Category(Base):
    """Modelo de categoria de produtos"""
    __tablename__ = "categories"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    description = Column(Text)
    icon = Column(String(50))  # Classe do ícone (ex: fa-download)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relacionamentos
    products = relationship("Product", back_populates="category")
    
    def __repr__(self):
        return f"<Category(name='{self.name}')>"

class Product(Base):
    """Modelo de produto"""
    __tablename__ = "products"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    price = Column(Float, nullable=False)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=False)
    duration_days = Column(Integer, default=30)  # Duração da licença em dias
    image_url = Column(String(500))
    download_url = Column(String(500))
    requirements = Column(Text)  # Requisitos do sistema
    tags = Column(String(500))  # Tags separadas por vírgula
    is_active = Column(Boolean, default=True)
    is_featured = Column(Boolean, default=False)
    download_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relacionamentos
    category = relationship("Category", back_populates="products")
    licenses = relationship("License", back_populates="product")
    transactions = relationship("Transaction", back_populates="product")
    downloads = relationship("Download", back_populates="product")
    
    def __repr__(self):
        return f"<Product(name='{self.name}', price={self.price})>"
    
    @property
    def tags_list(self):
        """Retorna lista de tags"""
        return [tag.strip() for tag in (self.tags or "").split(",") if tag.strip()]

class License(Base):
    """Modelo de licença"""
    __tablename__ = "licenses"
    
    id = Column(Integer, primary_key=True, index=True)
    license_key = Column(String(255), unique=True, nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    hwid = Column(String(255))  # Hardware ID
    status = Column(String(20), default="active")  # active, expired, suspended
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)
    last_verified = Column(DateTime)
    
    # Relacionamentos
    user = relationship("User", back_populates="licenses")
    product = relationship("Product", back_populates="licenses")
    downloads = relationship("Download", back_populates="license")
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.license_key:
            self.license_key = str(uuid.uuid4()).replace("-", "").upper()
    
    def __repr__(self):
        return f"<License(key='{self.license_key}', status='{self.status}')>"
    
    @property
    def is_expired(self):
        """Verifica se a licença está expirada"""
        return datetime.utcnow() > self.expires_at
    
    @property
    def days_remaining(self):
        """Retorna dias restantes da licença"""
        if self.is_expired:
            return 0
        return (self.expires_at - datetime.utcnow()).days

class Transaction(Base):
    """Modelo de transação"""
    __tablename__ = "transactions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    amount = Column(Float, nullable=False)
    payment_id = Column(String(255), unique=True, index=True)  # ID do Infinite Pay
    payment_method = Column(String(50))
    status = Column(String(20), default="pending")  # pending, approved, rejected, expired
    gateway_response = Column(JSON)  # Resposta completa do gateway
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relacionamentos
    user = relationship("User", back_populates="transactions")
    product = relationship("Product", back_populates="transactions")
    
    def __repr__(self):
        return f"<Transaction(id={self.id}, amount={self.amount}, status='{self.status}')>"

class Download(Base):
    """Modelo de download"""
    __tablename__ = "downloads"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    license_id = Column(Integer, ForeignKey("licenses.id"), nullable=False)
    ip_address = Column(String(45))
    user_agent = Column(String(500))
    downloaded_at = Column(DateTime, default=datetime.utcnow)
    
    # Relacionamentos
    user = relationship("User", back_populates="downloads")
    product = relationship("Product", back_populates="downloads")
    license = relationship("License", back_populates="downloads")
    
    def __repr__(self):
        return f"<Download(user_id={self.user_id}, product_id={self.product_id})>"

class SecurityLog(Base):
    """Modelo de log de segurança"""
    __tablename__ = "security_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    event_type = Column(String(50), nullable=False)  # login, failed_login, etc.
    user_id = Column(Integer, ForeignKey("users.id"))
    ip_address = Column(String(45))
    user_agent = Column(String(500))
    details = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<SecurityLog(event='{self.event_type}', user_id={self.user_id})>"

class PasswordReset(Base):
    """Modelo de reset de senha"""
    __tablename__ = "password_resets"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    token = Column(String(255), unique=True, nullable=False, index=True)
    expires_at = Column(DateTime, nullable=False)
    is_used = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.token:
            self.token = str(uuid.uuid4()).replace("-", "")
        if not self.expires_at:
            self.expires_at = datetime.utcnow() + timedelta(hours=1)
    
    def __repr__(self):
        return f"<PasswordReset(user_id={self.user_id}, is_used={self.is_used})>"
    
    @property
    def is_expired(self):
        """Verifica se o token está expirado"""
        return datetime.utcnow() > self.expires_at
