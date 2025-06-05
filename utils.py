import os
import re
import hashlib
import secrets
import string
from datetime import datetime
from typing import Optional, List, Dict, Any
from werkzeug.utils import secure_filename
from sqlalchemy.orm import Session
from models import AdminLog, User

# Configurações de upload
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'svg', 'zip', 'rar', '7z', 'exe', 'msi', 'dmg', 'pkg', 'deb', 'rpm'}
MAX_FILE_SIZE = 500 * 1024 * 1024  # 500MB

def allowed_file(filename: str) -> bool:
    """Verifica se o arquivo tem extensão permitida"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def secure_filename(filename: str) -> str:
    """Gera nome seguro para arquivo"""
    if not filename:
        return ''
    
    # Remover caracteres perigosos
    filename = re.sub(r'[^\w\s.-]', '', filename)
    
    # Adicionar timestamp para evitar conflitos
    name, ext = os.path.splitext(filename)
    timestamp = str(int(datetime.utcnow().timestamp()))
    
    return f"{name}_{timestamp}{ext}"

def generate_unique_filename(original_filename: str) -> str:
    """Gera nome único para arquivo"""
    name, ext = os.path.splitext(original_filename)
    unique_id = secrets.token_hex(8)
    timestamp = str(int(datetime.utcnow().timestamp()))
    
    # Sanitizar nome
    name = re.sub(r'[^\w\s.-]', '', name)[:50]
    
    return f"{name}_{timestamp}_{unique_id}{ext}"

def get_file_hash(file_path: str) -> str:
    """Calcula hash MD5 do arquivo"""
    hash_md5 = hashlib.md5()
    try:
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    except Exception:
        return ""

def format_file_size(size_bytes: int) -> str:
    """Formata tamanho do arquivo para exibição"""
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB", "TB"]
    size_index = 0
    
    while size_bytes >= 1024 and size_index < len(size_names) - 1:
        size_bytes /= 1024.0
        size_index += 1
    
    return f"{size_bytes:.1f} {size_names[size_index]}"

def validate_email(email: str) -> bool:
    """Valida formato de email"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_username(username: str) -> bool:
    """Valida nome de usuário"""
    # Deve ter entre 3 e 30 caracteres, apenas letras, números e underscore
    pattern = r'^[a-zA-Z0-9_]{3,30}$'
    return re.match(pattern, username) is not None

def sanitize_string(text: str) -> str:
    """Sanitiza string removendo caracteres perigosos"""
    if not text:
        return ""
    
    # Remover tags HTML
    text = re.sub(r'<[^>]+>', '', text)
    
    # Remover caracteres perigosos
    dangerous_chars = ['<', '>', '"', "'", '&', '\x00', '\r', '\n']
    for char in dangerous_chars:
        text = text.replace(char, '')
    
    return text.strip()

def generate_random_string(length: int = 16) -> str:
    """Gera string aleatória"""
    chars = string.ascii_letters + string.digits
    return ''.join(secrets.choice(chars) for _ in range(length))

def get_client_ip(request) -> str:
    """Obtém IP real do cliente"""
    # Verificar headers de proxy
    forwarded_for = request.headers.get('X-Forwarded-For')
    if forwarded_for:
        return forwarded_for.split(',')[0].strip()
    
    real_ip = request.headers.get('X-Real-IP')
    if real_ip:
        return real_ip
    
    return request.client.host

def log_action(
    db: Session,
    user_id: Optional[int],
    action: str,
    description: str,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None
) -> None:
    """Registra ação no log administrativo"""
    
    try:
        admin_log = AdminLog(
            user_id=user_id,
            action=action,
            description=description,
            ip_address=ip_address,
            user_agent=user_agent,
            created_at=datetime.utcnow()
        )
        
        db.add(admin_log)
        db.commit()
        
    except Exception as e:
        print(f"Error logging action: {e}")
        db.rollback()

def mask_email(email: str) -> str:
    """Mascara email para exibição"""
    if not email or '@' not in email:
        return email
    
    local, domain = email.split('@', 1)
    
    if len(local) <= 2:
        masked_local = '*' * len(local)
    else:
        masked_local = local[0] + '*' * (len(local) - 2) + local[-1]
    
    return f"{masked_local}@{domain}"

def mask_license_key(license_key: str) -> str:
    """Mascara chave de licença para exibição"""
    if not license_key:
        return ""
    
    if len(license_key) <= 8:
        return '*' * len(license_key)
    
    return license_key[:4] + '*' * (len(license_key) - 8) + license_key[-4:]

def format_currency(amount: float, currency: str = 'BRL') -> str:
    """Formata valor monetário"""
    if currency == 'BRL':
        return f"R$ {amount:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
    else:
        return f"{amount:,.2f}"

def parse_tags(tags_string: str) -> List[str]:
    """Converte string de tags em lista"""
    if not tags_string:
        return []
    
    tags = [tag.strip() for tag in tags_string.split(',')]
    return [tag for tag in tags if tag]

def format_tags(tags_list: List[str]) -> str:
    """Converte lista de tags em string"""
    return ', '.join(tags_list) if tags_list else ''

def calculate_password_strength(password: str) -> Dict[str, Any]:
    """Calcula força da senha"""
    score = 0
    feedback = []
    
    # Critérios de força
    if len(password) >= 8:
        score += 1
    else:
        feedback.append("Use pelo menos 8 caracteres")
    
    if len(password) >= 12:
        score += 1
    
    if re.search(r'[a-z]', password):
        score += 1
    else:
        feedback.append("Inclua letras minúsculas")
    
    if re.search(r'[A-Z]', password):
        score += 1
    else:
        feedback.append("Inclua letras maiúsculas")
    
    if re.search(r'\d', password):
        score += 1
    else:
        feedback.append("Inclua números")
    
    if re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        score += 1
    else:
        feedback.append("Inclua caracteres especiais")
    
    # Determinar nível
    if score <= 2:
        level = "Fraca"
        color = "danger"
    elif score <= 4:
        level = "Média"
        color = "warning"
    elif score <= 5:
        level = "Forte"
        color = "success"
    else:
        level = "Muito Forte"
        color = "success"
    
    return {
        "score": score,
        "level": level,
        "color": color,
        "feedback": feedback
    }

def format_datetime(dt: datetime, format_type: str = 'full') -> str:
    """Formata data/hora para exibição"""
    if not dt:
        return ""
    
    if format_type == 'date':
        return dt.strftime('%d/%m/%Y')
    elif format_type == 'time':
        return dt.strftime('%H:%M')
    elif format_type == 'datetime':
        return dt.strftime('%d/%m/%Y %H:%M')
    else:  # full
        return dt.strftime('%d/%m/%Y às %H:%M:%S')

def time_ago(dt: datetime) -> str:
    """Retorna tempo decorrido em formato legível"""
    if not dt:
        return ""
    
    now = datetime.utcnow()
    diff = now - dt
    
    seconds = diff.total_seconds()
    
    if seconds < 60:
        return "agora"
    elif seconds < 3600:
        minutes = int(seconds // 60)
        return f"{minutes} min atrás"
    elif seconds < 86400:
        hours = int(seconds // 3600)
        return f"{hours}h atrás"
    elif seconds < 2592000:  # 30 dias
        days = int(seconds // 86400)
        return f"{days} dias atrás"
    else:
        return format_datetime(dt, 'date')

def validate_hwid(hwid: str) -> bool:
    """Valida formato do HWID"""
    if not hwid:
        return False
    
    # HWID deve ter 32 caracteres hexadecimais
    pattern = r'^[a-fA-F0-9]{32}$'
    return re.match(pattern, hwid) is not None

def clean_filename(filename: str) -> str:
    """Limpa nome do arquivo removendo caracteres problemáticos"""
    if not filename:
        return ""
    
    # Remover caracteres especiais e espaços
    filename = re.sub(r'[^\w\s.-]', '', filename)
    filename = re.sub(r'\s+', '_', filename)
    
    return filename

def get_mime_type(filename: str) -> str:
    """Obtém tipo MIME baseado na extensão"""
    ext = filename.lower().split('.')[-1] if '.' in filename else ''
    
    mime_types = {
        'png': 'image/png',
        'jpg': 'image/jpeg',
        'jpeg': 'image/jpeg',
        'gif': 'image/gif',
        'webp': 'image/webp',
        'svg': 'image/svg+xml',
        'zip': 'application/zip',
        'rar': 'application/x-rar-compressed',
        '7z': 'application/x-7z-compressed',
        'exe': 'application/x-msdownload',
        'msi': 'application/x-msdownload',
        'dmg': 'application/x-apple-diskimage',
        'pkg': 'application/x-newton-compatible-pkg',
        'deb': 'application/vnd.debian.binary-package',
        'rpm': 'application/x-rpm'
    }
    
    return mime_types.get(ext, 'application/octet-stream')

def truncate_text(text: str, max_length: int = 100) -> str:
    """Trunca texto com reticências"""
    if not text:
        return ""
    
    if len(text) <= max_length:
        return text
    
    return text[:max_length - 3] + "..."

def is_safe_url(url: str) -> bool:
    """Verifica se URL é segura para redirecionamento"""
    if not url:
        return False
    
    # Permitir apenas URLs relativas ou do mesmo domínio
    if url.startswith('/'):
        return True
    
    # Verificar se começa com protocolo perigoso
    dangerous_protocols = ['javascript:', 'data:', 'vbscript:', 'file:']
    for protocol in dangerous_protocols:
        if url.lower().startswith(protocol):
            return False
    
    return True

def generate_api_key() -> str:
    """Gera chave de API"""
    prefix = "fov_"
    random_part = secrets.token_hex(16)
    return f"{prefix}{random_part}"

def rate_limit_key(ip: str, endpoint: str) -> str:
    """Gera chave para rate limiting"""
    return f"rate_limit:{ip}:{endpoint}"

class FileUploadError(Exception):
    """Exceção para erros de upload"""
    pass

def validate_upload(file, max_size: int = MAX_FILE_SIZE) -> None:
    """Valida arquivo para upload"""
    if not file:
        raise FileUploadError("Nenhum arquivo enviado")
    
    if file.filename == '':
        raise FileUploadError("Nome de arquivo vazio")
    
    if not allowed_file(file.filename):
        raise FileUploadError("Tipo de arquivo não permitido")
    
    # Verificar tamanho do arquivo (se possível)
    if hasattr(file, 'content_length') and file.content_length:
        if file.content_length > max_size:
            raise FileUploadError(f"Arquivo muito grande. Máximo: {format_file_size(max_size)}")

def create_directories():
    """Cria diretórios necessários"""
    directories = [
        'static/uploads',
        'static/uploads/products',
        'static/uploads/avatars',
        'static/uploads/temp'
    ]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)

# Inicializar diretórios na importação
create_directories()
