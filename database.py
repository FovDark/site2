import os
import asyncio
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from models import Base, Category, User
from config import get_config
import logging

logger = logging.getLogger(__name__)

# Obter configurações da aplicação
config = get_config()
DATABASE_URL = config.get_database_url()

logger.info(f"Conectando ao banco: {'PostgreSQL (Supabase)' if 'postgresql' in DATABASE_URL else 'SQLite'}")

# Engine síncrono para aplicação principal - otimizado para Supabase
if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(
        DATABASE_URL,
        echo=False,
        connect_args={"check_same_thread": False}
    )
else:
    # Configuração otimizada para Supabase PostgreSQL
    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,
        pool_recycle=300,
        pool_size=10,
        max_overflow=20,
        pool_timeout=30,
        echo=False,
        connect_args={
            "sslmode": "require",
            "connect_timeout": 30,
            "application_name": "FovDark_Gaming"
        }
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    """Dependency para obter sessão do banco"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def create_tables():
    """Criar todas as tabelas e dados iniciais"""
    try:
        # Criar todas as tabelas
        Base.metadata.create_all(bind=engine)
        logger.info("Tabelas criadas com sucesso")
        
        # Criar dados iniciais
        create_initial_data()
        
    except Exception as e:
        logger.error(f"Erro ao criar tabelas: {e}")
        raise

def create_initial_data():
    """Criar dados iniciais do sistema"""
    db = SessionLocal()
    try:
        # Verificar se já existem categorias
        existing_categories = db.query(Category).count()
        if existing_categories == 0:
            # Criar categorias padrão
            categories = [
                Category(
                    name="ISOs Customizadas",
                    description="Sistemas operacionais personalizados e otimizados",
                    icon="fa-compact-disc"
                ),
                Category(
                    name="Programas",
                    description="Software e aplicativos diversos",
                    icon="fa-desktop"
                ),
                Category(
                    name="Otimizadores",
                    description="Ferramentas para otimização de sistema",
                    icon="fa-rocket"
                ),
                Category(
                    name="Cheats & Trainers",
                    description="Modificadores para jogos",
                    icon="fa-gamepad"
                ),
                Category(
                    name="Mods",
                    description="Modificações para jogos e aplicativos",
                    icon="fa-puzzle-piece"
                )
            ]
            
            for category in categories:
                db.add(category)
            
            db.commit()
            logger.info("Categorias iniciais criadas")
        
        # Verificar se já existe usuário admin
        existing_admin = db.query(User).filter(User.is_admin == True).first()
        if not existing_admin:
            # Importar hash_password aqui para evitar importação circular
            from auth import hash_password
            
            # Criar usuário admin padrão
            admin_user = User(
                username="admin",
                email="admin@fovdark.com",
                password_hash=hash_password("admin123"),
                is_active=True,
                is_admin=True
            )
            
            db.add(admin_user)
            db.commit()
            logger.info("Usuário admin criado: admin/admin123")
            
    except Exception as e:
        logger.error(f"Erro ao criar dados iniciais: {e}")
        db.rollback()
    finally:
        db.close()

def init_db():
    """Inicializar banco de dados de forma síncrona"""
    try:
        Base.metadata.create_all(bind=engine)
        
        # Criar dados iniciais
        create_initial_data()
        
        logger.info("Banco de dados inicializado com sucesso")
        
    except Exception as e:
        logger.error(f"Erro ao inicializar banco: {e}")
        raise

def test_connection():
    """Testar conexão com o banco"""
    try:
        db = SessionLocal()
        from sqlalchemy import text
        db.execute(text("SELECT 1"))
        db.close()
        logger.info("Conexão com banco de dados OK")
        return True
    except Exception as e:
        logger.error(f"Erro na conexão com banco: {e}")
        return False

def reset_database():
    """Resetar banco de dados (CUIDADO: apaga todos os dados)"""
    try:
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)
        
        # Recriar dados iniciais
        create_initial_data()
        
        logger.info("Banco de dados resetado com sucesso")
        
    except Exception as e:
        logger.error(f"Erro ao resetar banco: {e}")
        raise

if __name__ == "__main__":
    # Testar conexão e inicializar banco
    if test_connection():
        init_db()
    else:
        logger.error("Falha na conexão com o banco de dados")
