"""
Configurações centralizadas da aplicação FovDark Gaming
"""
import os
from typing import Optional
from datetime import timedelta

class Config:
    """Configurações base da aplicação"""
    
    # Database Configuration
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./fovdark.db")
    
    # JWT Configuration
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "dev-secret-key-change-in-production")
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
    
    # Application Configuration
    SECRET_KEY: str = os.getenv("SECRET_KEY", "dev-flask-secret-change-in-production")
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    
    # Security Configuration
    ALLOWED_HOSTS: list = os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")
    CORS_ORIGINS: list = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000").split(",")
    
    # Port Configuration for Production
    PORT: int = int(os.getenv("PORT", "5000"))
    
    # Email Configuration
    SMTP_SERVER: Optional[str] = os.getenv("SMTP_SERVER")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USERNAME: Optional[str] = os.getenv("SMTP_USERNAME")
    SMTP_PASSWORD: Optional[str] = os.getenv("SMTP_PASSWORD")
    
    # Payment Gateway Configuration
    INFINITE_PAY_API_KEY: Optional[str] = os.getenv("INFINITE_PAY_API_KEY")
    INFINITE_PAY_WEBHOOK_SECRET: Optional[str] = os.getenv("INFINITE_PAY_WEBHOOK_SECRET")
    
    # File Upload Configuration
    MAX_CONTENT_LENGTH: int = 16 * 1024 * 1024  # 16MB
    UPLOAD_FOLDER: str = os.getenv("UPLOAD_FOLDER", "uploads")
    ALLOWED_EXTENSIONS: set = {"png", "jpg", "jpeg", "gif", "pdf", "zip", "rar"}
    
    # Rate Limiting
    RATELIMIT_STORAGE_URL: str = os.getenv("RATELIMIT_STORAGE_URL", "memory://")
    
    # Logging Configuration
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE: str = os.getenv("LOG_FILE", "app.log")
    
    @classmethod
    def is_production(cls) -> bool:
        """Verifica se está em ambiente de produção"""
        return cls.ENVIRONMENT.lower() == "production"
    
    @classmethod
    def is_development(cls) -> bool:
        """Verifica se está em ambiente de desenvolvimento"""
        return cls.ENVIRONMENT.lower() == "development"
    
    @classmethod
    def get_database_url(cls) -> str:
        """Retorna a URL do banco de dados configurada"""
        return cls.DATABASE_URL
    
    @classmethod
    def validate_config(cls) -> list:
        """Valida configurações críticas e retorna lista de erros"""
        errors = []
        
        if cls.is_production():
            if cls.JWT_SECRET_KEY == "dev-secret-key-change-in-production":
                errors.append("JWT_SECRET_KEY deve ser alterado em produção")
            
            if cls.SECRET_KEY == "dev-flask-secret-change-in-production":
                errors.append("SECRET_KEY deve ser alterado em produção")
            
            if not cls.DATABASE_URL or cls.DATABASE_URL.startswith("sqlite"):
                errors.append("DATABASE_URL deve ser PostgreSQL em produção")
        
        return errors

class DevelopmentConfig(Config):
    """Configurações para desenvolvimento"""
    DEBUG = True
    ENVIRONMENT = "development"

class ProductionConfig(Config):
    """Configurações para produção"""
    DEBUG = False
    ENVIRONMENT = "production"

class TestingConfig(Config):
    """Configurações para testes"""
    DEBUG = True
    ENVIRONMENT = "testing"
    DATABASE_URL = "sqlite:///:memory:"

# Mapeamento de configurações por ambiente
config_by_name = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig
}

def get_config() -> Config:
    """Retorna a configuração baseada na variável de ambiente"""
    env = os.getenv("ENVIRONMENT", "development").lower()
    return config_by_name.get(env, DevelopmentConfig)()