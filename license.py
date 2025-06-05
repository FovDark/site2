import hashlib
import platform
import subprocess
import uuid
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from models import License, Product, User
import logging

logger = logging.getLogger(__name__)

def get_hwid() -> str:
    """Obter Hardware ID do sistema"""
    try:
        # Combinar informações do sistema para criar HWID único
        system_info = []
        
        # Informações básicas do sistema
        system_info.append(platform.system())
        system_info.append(platform.machine())
        system_info.append(platform.processor())
        
        # Tentar obter informações específicas do hardware
        try:
            if platform.system() == "Windows":
                # Windows - usar wmic
                cpu_id = subprocess.check_output("wmic cpu get ProcessorId", shell=True).decode().strip()
                motherboard_id = subprocess.check_output("wmic baseboard get SerialNumber", shell=True).decode().strip()
                system_info.extend([cpu_id, motherboard_id])
            elif platform.system() == "Linux":
                # Linux - usar /proc/cpuinfo e dmidecode
                try:
                    with open("/proc/cpuinfo", "r") as f:
                        cpu_info = f.read()
                        # Extrair serial do processador se disponível
                        for line in cpu_info.split("\n"):
                            if "Serial" in line:
                                system_info.append(line.split(":")[1].strip())
                                break
                except:
                    pass
                
                try:
                    machine_id = subprocess.check_output("cat /etc/machine-id", shell=True).decode().strip()
                    system_info.append(machine_id)
                except:
                    pass
            elif platform.system() == "Darwin":
                # macOS - usar system_profiler
                try:
                    serial = subprocess.check_output("system_profiler SPHardwareDataType | grep 'Serial Number'", shell=True).decode().strip()
                    system_info.append(serial)
                except:
                    pass
        except Exception as e:
            logger.warning(f"Erro ao obter informações específicas do hardware: {e}")
        
        # Se não conseguiu obter informações específicas, usar UUID do sistema
        if len(system_info) <= 3:
            try:
                system_uuid = str(uuid.getnode())  # MAC address como fallback
                system_info.append(system_uuid)
            except:
                # Último recurso - gerar baseado em informações disponíveis
                system_info.append(str(hash(str(platform.uname()))))
        
        # Criar hash único
        combined_info = "|".join(system_info)
        hwid = hashlib.sha256(combined_info.encode()).hexdigest()[:32].upper()
        
        return hwid
        
    except Exception as e:
        logger.error(f"Erro ao obter HWID: {e}")
        # Fallback - gerar HWID baseado em informações básicas
        fallback_info = f"{platform.system()}|{platform.machine()}|{platform.processor()}"
        return hashlib.sha256(fallback_info.encode()).hexdigest()[:32].upper()

def create_license(db: Session, user_id: int, product_id: int, duration_days: int = 30, hwid: str = None) -> License:
    """Criar nova licença"""
    try:
        # Verificar se produto existe
        product = db.query(Product).filter(Product.id == product_id).first()
        if not product:
            raise ValueError("Produto não encontrado")
        
        # Verificar se usuário existe
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError("Usuário não encontrado")
        
        # Calcular data de expiração
        expires_at = datetime.utcnow() + timedelta(days=duration_days)
        
        # Criar licença
        license_obj = License(
            user_id=user_id,
            product_id=product_id,
            hwid=hwid,
            status="active",
            expires_at=expires_at
        )
        
        db.add(license_obj)
        db.commit()
        db.refresh(license_obj)
        
        logger.info(f"Licença criada: {license_obj.license_key} para usuário {user.username}")
        return license_obj
        
    except Exception as e:
        logger.error(f"Erro ao criar licença: {e}")
        db.rollback()
        raise

def verify_license(db: Session, license_key: str, hwid: str = None) -> tuple[bool, License]:
    """Verificar validade da licença"""
    try:
        # Buscar licença
        license_obj = db.query(License).filter(License.license_key == license_key).first()
        
        if not license_obj:
            logger.warning(f"Licença não encontrada: {license_key}")
            return False, None
        
        # Verificar se está expirada
        if license_obj.is_expired:
            logger.warning(f"Licença expirada: {license_key}")
            license_obj.status = "expired"
            db.commit()
            return False, license_obj
        
        # Verificar status
        if license_obj.status != "active":
            logger.warning(f"Licença não ativa: {license_key} - Status: {license_obj.status}")
            return False, license_obj
        
        # Verificar HWID se fornecido
        if hwid:
            if license_obj.hwid is None:
                # Primeira verificação - associar HWID
                license_obj.hwid = hwid
                logger.info(f"HWID associado à licença: {license_key}")
            elif license_obj.hwid != hwid:
                logger.warning(f"HWID não corresponde para licença: {license_key}")
                return False, license_obj
        
        # Atualizar última verificação
        license_obj.last_verified = datetime.utcnow()
        db.commit()
        
        logger.info(f"Licença verificada com sucesso: {license_key}")
        return True, license_obj
        
    except Exception as e:
        logger.error(f"Erro ao verificar licença {license_key}: {e}")
        return False, None

def extend_license(db: Session, license_key: str, additional_days: int) -> bool:
    """Estender duração da licença"""
    try:
        license_obj = db.query(License).filter(License.license_key == license_key).first()
        
        if not license_obj:
            return False
        
        # Estender data de expiração
        license_obj.expires_at = license_obj.expires_at + timedelta(days=additional_days)
        
        # Se estava expirada, reativar
        if license_obj.status == "expired" and not license_obj.is_expired:
            license_obj.status = "active"
        
        db.commit()
        
        logger.info(f"Licença estendida: {license_key} por {additional_days} dias")
        return True
        
    except Exception as e:
        logger.error(f"Erro ao estender licença {license_key}: {e}")
        db.rollback()
        return False

def revoke_license(db: Session, license_key: str, reason: str = None) -> bool:
    """Revogar licença"""
    try:
        license_obj = db.query(License).filter(License.license_key == license_key).first()
        
        if not license_obj:
            return False
        
        license_obj.status = "revoked"
        db.commit()
        
        logger.info(f"Licença revogada: {license_key} - Motivo: {reason}")
        return True
        
    except Exception as e:
        logger.error(f"Erro ao revogar licença {license_key}: {e}")
        db.rollback()
        return False

def get_user_licenses(db: Session, user_id: int) -> list[License]:
    """Obter todas as licenças do usuário"""
    try:
        licenses = db.query(License).filter(License.user_id == user_id).all()
        return licenses
        
    except Exception as e:
        logger.error(f"Erro ao obter licenças do usuário {user_id}: {e}")
        return []

def get_active_licenses(db: Session, user_id: int) -> list[License]:
    """Obter licenças ativas do usuário"""
    try:
        licenses = db.query(License).filter(
            License.user_id == user_id,
            License.status == "active",
            License.expires_at > datetime.utcnow()
        ).all()
        
        return licenses
        
    except Exception as e:
        logger.error(f"Erro ao obter licenças ativas do usuário {user_id}: {e}")
        return []

def check_license_for_product(db: Session, user_id: int, product_id: int) -> License:
    """Verificar se usuário tem licença ativa para produto específico"""
    try:
        license_obj = db.query(License).filter(
            License.user_id == user_id,
            License.product_id == product_id,
            License.status == "active",
            License.expires_at > datetime.utcnow()
        ).first()
        
        return license_obj
        
    except Exception as e:
        logger.error(f"Erro ao verificar licença do produto {product_id} para usuário {user_id}: {e}")
        return None

def cleanup_expired_licenses(db: Session) -> int:
    """Limpar licenças expiradas (atualizar status)"""
    try:
        expired_licenses = db.query(License).filter(
            License.expires_at <= datetime.utcnow(),
            License.status == "active"
        ).all()
        
        count = 0
        for license_obj in expired_licenses:
            license_obj.status = "expired"
            count += 1
        
        db.commit()
        
        if count > 0:
            logger.info(f"Limpeza realizada: {count} licenças expiradas atualizadas")
        
        return count
        
    except Exception as e:
        logger.error(f"Erro na limpeza de licenças expiradas: {e}")
        db.rollback()
        return 0

def generate_license_report(db: Session, user_id: int = None) -> dict:
    """Gerar relatório de licenças"""
    try:
        query = db.query(License)
        if user_id:
            query = query.filter(License.user_id == user_id)
        
        all_licenses = query.all()
        
        active_count = len([l for l in all_licenses if l.status == "active" and not l.is_expired])
        expired_count = len([l for l in all_licenses if l.is_expired])
        revoked_count = len([l for l in all_licenses if l.status == "revoked"])
        suspended_count = len([l for l in all_licenses if l.status == "suspended"])
        
        # Licenças por produto
        product_stats = {}
        for license_obj in all_licenses:
            product_name = license_obj.product.name
            if product_name not in product_stats:
                product_stats[product_name] = {"total": 0, "active": 0}
            product_stats[product_name]["total"] += 1
            if license_obj.status == "active" and not license_obj.is_expired:
                product_stats[product_name]["active"] += 1
        
        return {
            "total": len(all_licenses),
            "active": active_count,
            "expired": expired_count,
            "revoked": revoked_count,
            "suspended": suspended_count,
            "by_product": product_stats
        }
        
    except Exception as e:
        logger.error(f"Erro ao gerar relatório de licenças: {e}")
        return {}

class LicenseManager:
    """Gerenciador de licenças"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_license(self, user_id: int, product_id: int, duration_days: int = 30, hwid: str = None) -> License:
        """Criar nova licença"""
        return create_license(self.db, user_id, product_id, duration_days, hwid)
    
    def verify_license(self, license_key: str, hwid: str = None) -> tuple[bool, License]:
        """Verificar licença"""
        return verify_license(self.db, license_key, hwid)
    
    def extend_license(self, license_key: str, additional_days: int) -> bool:
        """Estender licença"""
        return extend_license(self.db, license_key, additional_days)
    
    def revoke_license(self, license_key: str, reason: str = None) -> bool:
        """Revogar licença"""
        return revoke_license(self.db, license_key, reason)
    
    def cleanup_expired(self) -> int:
        """Limpar licenças expiradas"""
        return cleanup_expired_licenses(self.db)
    
    def get_user_licenses(self, user_id: int) -> list[License]:
        """Obter licenças do usuário"""
        return get_user_licenses(self.db, user_id)
    
    def get_active_licenses(self, user_id: int) -> list[License]:
        """Obter licenças ativas do usuário"""
        return get_active_licenses(self.db, user_id)
