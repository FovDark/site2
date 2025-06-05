import os
import re
import bleach
import hashlib
import logging
from datetime import datetime
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from models import SecurityLog
from typing import Dict, Any
import ipaddress
import user_agents

logger = logging.getLogger(__name__)

# Configurações de segurança
ALLOWED_TAGS = [
    'b', 'i', 'u', 'em', 'strong', 'p', 'br', 'ul', 'ol', 'li'
]

ALLOWED_ATTRIBUTES = {
    '*': ['class'],
    'a': ['href', 'title'],
    'img': ['src', 'alt', 'width', 'height']
}

# Headers de segurança
SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "X-XSS-Protection": "1; mode=block",
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
    "Content-Security-Policy": (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' https://cdnjs.cloudflare.com https://cdn.jsdelivr.net; "
        "style-src 'self' 'unsafe-inline' https://cdnjs.cloudflare.com https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com; "
        "img-src 'self' data: https:; "
        "connect-src 'self' https:; "
        "frame-ancestors 'none';"
    ),
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "geolocation=(), microphone=(), camera=()"
}

def add_security_headers(response: Response) -> Response:
    """Adicionar headers de segurança à resposta"""
    try:
        for header, value in SECURITY_HEADERS.items():
            response.headers[header] = value
        return response
    except Exception as e:
        logger.error(f"Erro ao adicionar headers de segurança: {e}")
        return response

def validate_input(value: str, input_type: str = "general") -> str:
    """Validar e sanitizar entrada do usuário"""
    try:
        if not value:
            return ""
        
        # Remover espaços extras
        value = value.strip()
        
        # Validações específicas por tipo
        if input_type == "email":
            return validate_email(value)
        elif input_type == "username":
            return validate_username(value)
        elif input_type == "password":
            return validate_password_input(value)
        elif input_type == "url":
            return validate_url(value)
        elif input_type == "html":
            return sanitize_html(value)
        else:
            # Sanitização geral
            return sanitize_general_input(value)
            
    except Exception as e:
        logger.error(f"Erro na validação de entrada: {e}")
        raise ValueError("Entrada inválida")

def validate_email(email: str) -> str:
    """Validar formato de email"""
    email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    
    if not re.match(email_regex, email):
        raise ValueError("Formato de email inválido")
    
    if len(email) > 255:
        raise ValueError("Email muito longo")
    
    return email.lower()

def validate_username(username: str) -> str:
    """Validar username"""
    # Apenas letras, números, underscore e hífen
    username_regex = r'^[a-zA-Z0-9_-]+$'
    
    if not re.match(username_regex, username):
        raise ValueError("Username deve conter apenas letras, números, _ e -")
    
    if len(username) < 3 or len(username) > 30:
        raise ValueError("Username deve ter entre 3 e 30 caracteres")
    
    return username.lower()

def validate_password_input(password: str) -> str:
    """Validar senha (apenas verificações básicas)"""
    if len(password) < 8:
        raise ValueError("Senha deve ter pelo menos 8 caracteres")
    
    if len(password) > 128:
        raise ValueError("Senha muito longa")
    
    return password

def validate_url(url: str) -> str:
    """Validar URL"""
    url_regex = r'^https?://[^\s/$.?#].[^\s]*$'
    
    if not re.match(url_regex, url):
        raise ValueError("URL inválida")
    
    return url

def sanitize_html(html: str) -> str:
    """Sanitizar conteúdo HTML"""
    try:
        return bleach.clean(
            html,
            tags=ALLOWED_TAGS,
            attributes=ALLOWED_ATTRIBUTES,
            strip=True
        )
    except Exception as e:
        logger.error(f"Erro ao sanitizar HTML: {e}")
        return ""

def sanitize_general_input(value: str) -> str:
    """Sanitização geral para prevenir XSS"""
    try:
        # Remover caracteres perigosos
        dangerous_chars = ['<', '>', '"', "'", '&', 'javascript:', 'data:', 'vbscript:']
        
        for char in dangerous_chars:
            value = value.replace(char, '')
        
        # Limitar tamanho
        if len(value) > 1000:
            value = value[:1000]
        
        return value
        
    except Exception as e:
        logger.error(f"Erro na sanitização geral: {e}")
        return ""

def detect_sql_injection(value: str) -> bool:
    """Detectar tentativas de SQL injection"""
    try:
        sql_patterns = [
            r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|UNION)\b)",
            r"(\b(OR|AND)\s+\d+\s*=\s*\d+)",
            r"('|\"|;|--|\*|/\*|\*/)",
            r"(\b(SCRIPT|JAVASCRIPT|VBSCRIPT)\b)"
        ]
        
        value_upper = value.upper()
        
        for pattern in sql_patterns:
            if re.search(pattern, value_upper, re.IGNORECASE):
                return True
        
        return False
        
    except Exception as e:
        logger.error(f"Erro na detecção de SQL injection: {e}")
        return False

def detect_xss_attempt(value: str) -> bool:
    """Detectar tentativas de XSS"""
    try:
        xss_patterns = [
            r"<script[^>]*>.*?</script>",
            r"javascript:",
            r"on\w+\s*=",
            r"<iframe[^>]*>",
            r"<object[^>]*>",
            r"<embed[^>]*>",
            r"eval\s*\(",
            r"alert\s*\(",
            r"document\.cookie",
            r"window\.location"
        ]
        
        for pattern in xss_patterns:
            if re.search(pattern, value, re.IGNORECASE):
                return True
        
        return False
        
    except Exception as e:
        logger.error(f"Erro na detecção de XSS: {e}")
        return False

def get_client_ip(request: Request) -> str:
    """Obter IP real do cliente"""
    try:
        # Verificar headers de proxy
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            # Pegar o primeiro IP da lista
            ip = forwarded_for.split(",")[0].strip()
            return ip
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        # Fallback para IP direto
        return str(request.client.host)
        
    except Exception as e:
        logger.error(f"Erro ao obter IP do cliente: {e}")
        return "unknown"

def get_user_agent_info(request: Request) -> Dict[str, str]:
    """Obter informações do user agent"""
    try:
        user_agent_string = request.headers.get("User-Agent", "")
        user_agent = user_agents.parse(user_agent_string)
        
        return {
            "browser": f"{user_agent.browser.family} {user_agent.browser.version_string}",
            "os": f"{user_agent.os.family} {user_agent.os.version_string}",
            "device": user_agent.device.family,
            "is_mobile": user_agent.is_mobile,
            "is_bot": user_agent.is_bot,
            "raw": user_agent_string
        }
        
    except Exception as e:
        logger.error(f"Erro ao analisar user agent: {e}")
        return {
            "browser": "Unknown",
            "os": "Unknown",
            "device": "Unknown",
            "is_mobile": False,
            "is_bot": False,
            "raw": request.headers.get("User-Agent", "")
        }

def is_suspicious_ip(ip: str) -> bool:
    """Verificar se IP é suspeito"""
    try:
        ip_obj = ipaddress.ip_address(ip)
        
        # Verificar IPs privados/locais (não são suspeitos)
        if ip_obj.is_private or ip_obj.is_loopback:
            return False
        
        # Lista de ranges suspeitos (Tor, VPN conhecidos, etc.)
        suspicious_ranges = [
            # Adicionar ranges conhecidos de Tor, VPNs maliciosos, etc.
            # Este é um exemplo básico
        ]
        
        for range_str in suspicious_ranges:
            if ip_obj in ipaddress.ip_network(range_str):
                return True
        
        return False
        
    except Exception as e:
        logger.error(f"Erro ao verificar IP suspeito: {e}")
        return False

def log_security_event(event_type: str, details: Dict[str, Any], db: Session = None):
    """Registrar evento de segurança"""
    try:
        if not db:
            # Se não há sessão DB, apenas logar
            logger.warning(f"Evento de segurança: {event_type} - {details}")
            return
        
        # Criar log no banco
        security_log = SecurityLog(
            event_type=event_type,
            user_id=details.get("user_id"),
            ip_address=details.get("ip"),
            user_agent=details.get("user_agent"),
            details=details
        )
        
        db.add(security_log)
        db.commit()
        
        logger.info(f"Evento de segurança registrado: {event_type}")
        
    except Exception as e:
        logger.error(f"Erro ao registrar evento de segurança: {e}")

def check_rate_limit(ip: str, endpoint: str, limit: int = 10, window: int = 60) -> bool:
    """Verificar rate limiting (implementação básica em memória)"""
    try:
        # Em produção, usar Redis ou banco de dados
        # Esta é uma implementação simples para demonstração
        
        current_time = datetime.utcnow().timestamp()
        key = f"{ip}:{endpoint}"
        
        # Simular verificação de rate limit
        # Em implementação real, verificar no Redis/DB
        
        return True  # Permitir por padrão
        
    except Exception as e:
        logger.error(f"Erro na verificação de rate limit: {e}")
        return True

def hash_sensitive_data(data: str) -> str:
    """Hash de dados sensíveis para logs"""
    try:
        return hashlib.sha256(data.encode()).hexdigest()[:8]
    except Exception as e:
        logger.error(f"Erro ao hash dados sensíveis: {e}")
        return "unknown"

def validate_file_upload(filename: str, content: bytes, max_size: int = 5 * 1024 * 1024) -> Dict[str, Any]:
    """Validar upload de arquivo"""
    try:
        result = {
            "valid": False,
            "errors": [],
            "warnings": []
        }
        
        # Verificar tamanho
        if len(content) > max_size:
            result["errors"].append(f"Arquivo muito grande (max: {max_size/1024/1024:.1f}MB)")
            return result
        
        # Verificar extensão
        allowed_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg']
        file_ext = os.path.splitext(filename.lower())[1]
        
        if file_ext not in allowed_extensions:
            result["errors"].append("Tipo de arquivo não permitido")
            return result
        
        # Verificar magic bytes (assinatura do arquivo)
        magic_bytes = {
            b'\xff\xd8\xff': 'jpg',
            b'\x89\x50\x4e\x47': 'png',
            b'\x47\x49\x46': 'gif',
            b'RIFF': 'webp'
        }
        
        file_type = None
        for magic, ftype in magic_bytes.items():
            if content.startswith(magic):
                file_type = ftype
                break
        
        if not file_type and file_ext != '.svg':
            result["warnings"].append("Tipo de arquivo não reconhecido")
        
        # Verificar nome do arquivo
        safe_filename = re.sub(r'[^a-zA-Z0-9._-]', '', filename)
        if safe_filename != filename:
            result["warnings"].append("Nome do arquivo foi sanitizado")
        
        result["valid"] = len(result["errors"]) == 0
        result["safe_filename"] = safe_filename
        
        return result
        
    except Exception as e:
        logger.error(f"Erro na validação de arquivo: {e}")
        return {
            "valid": False,
            "errors": ["Erro interno na validação do arquivo"],
            "warnings": []
        }

class SecurityMiddleware:
    """Middleware de segurança"""
    
    def __init__(self):
        self.blocked_ips = set()
        self.suspicious_patterns = [
            r'\.php$',
            r'\.asp$',
            r'\.jsp$',
            r'/admin\.php',
            r'/wp-admin',
            r'/phpmyadmin'
        ]
    
    def is_blocked_request(self, request: Request) -> bool:
        """Verificar se requisição deve ser bloqueada"""
        try:
            path = request.url.path.lower()
            
            # Verificar padrões suspeitos
            for pattern in self.suspicious_patterns:
                if re.search(pattern, path):
                    return True
            
            # Verificar IP bloqueado
            client_ip = get_client_ip(request)
            if client_ip in self.blocked_ips:
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Erro na verificação de bloqueio: {e}")
            return False
    
    def block_ip(self, ip: str, reason: str = ""):
        """Bloquear IP"""
        try:
            self.blocked_ips.add(ip)
            logger.warning(f"IP bloqueado: {ip} - Motivo: {reason}")
        except Exception as e:
            logger.error(f"Erro ao bloquear IP: {e}")
    
    def unblock_ip(self, ip: str):
        """Desbloquear IP"""
        try:
            self.blocked_ips.discard(ip)
            logger.info(f"IP desbloqueado: {ip}")
        except Exception as e:
            logger.error(f"Erro ao desbloquear IP: {e}")

# Instância global do middleware
security_middleware = SecurityMiddleware()

def create_security_response(message: str, status_code: int = 403) -> JSONResponse:
    """Criar resposta de erro de segurança"""
    return JSONResponse(
        content={"error": message, "type": "security_error"},
        status_code=status_code
    )

def audit_log(action: str, user_id: int = None, details: Dict[str, Any] = None, db: Session = None):
    """Log de auditoria para ações importantes"""
    try:
        log_data = {
            "action": action,
            "user_id": user_id,
            "timestamp": datetime.utcnow().isoformat(),
            "details": details or {}
        }
        
        if db:
            log_security_event("audit", log_data, db)
        else:
            logger.info(f"Auditoria: {log_data}")
            
    except Exception as e:
        logger.error(f"Erro no log de auditoria: {e}")
