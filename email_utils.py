import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import logging
from jinja2 import Template
from models import User, License, Product

logger = logging.getLogger(__name__)

# Configurações de email
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USERNAME = os.getenv("SMTP_USERNAME", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
FROM_EMAIL = os.getenv("FROM_EMAIL", "noreply@fovdark.com")
FROM_NAME = os.getenv("FROM_NAME", "FovDark")

def send_email(to_email: str, subject: str, html_content: str, text_content: str = None) -> bool:
    """Enviar email via SMTP"""
    try:
        # Criar mensagem
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = f"{FROM_NAME} <{FROM_EMAIL}>"
        msg['To'] = to_email
        
        # Adicionar conteúdo texto se fornecido
        if text_content:
            part1 = MIMEText(text_content, 'plain', 'utf-8')
            msg.attach(part1)
        
        # Adicionar conteúdo HTML
        part2 = MIMEText(html_content, 'html', 'utf-8')
        msg.attach(part2)
        
        # Conectar ao servidor SMTP
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SMTP_USERNAME, SMTP_PASSWORD)
        
        # Enviar email
        server.send_message(msg)
        server.quit()
        
        logger.info(f"Email enviado com sucesso para: {to_email}")
        return True
        
    except Exception as e:
        logger.error(f"Erro ao enviar email para {to_email}: {e}")
        return False

def send_password_reset_email(email: str, reset_token: str) -> bool:
    """Enviar email de recuperação de senha"""
    try:
        reset_url = f"{os.getenv('SITE_URL', 'http://localhost:5000')}/reset-password?token={reset_token}"
        
        # Template HTML
        html_template = """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Recuperação de Senha - FovDark</title>
            <style>
                body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
                .container { max-width: 600px; margin: 0 auto; padding: 20px; }
                .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; text-align: center; }
                .content { background: #f8f9fa; padding: 30px; }
                .button { display: inline-block; background: #667eea; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; margin: 20px 0; }
                .footer { text-align: center; padding: 20px; color: #666; font-size: 12px; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🔐 FovDark - Recuperação de Senha</h1>
                </div>
                <div class="content">
                    <h2>Solicitação de Nova Senha</h2>
                    <p>Você solicitou a recuperação de sua senha no FovDark.</p>
                    <p>Clique no botão abaixo para definir uma nova senha:</p>
                    <p style="text-align: center;">
                        <a href="{{reset_url}}" class="button">🔑 Redefinir Senha</a>
                    </p>
                    <p><strong>Este link expira em 1 hora.</strong></p>
                    <p>Se você não solicitou esta recuperação, ignore este email.</p>
                </div>
                <div class="footer">
                    <p>© 2024 FovDark - Sistema de Licenças Digitais</p>
                    <p>Este é um email automático, não responda.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        template = Template(html_template)
        html_content = template.render(reset_url=reset_url)
        
        # Conteúdo texto simples
        text_content = f"""
        FovDark - Recuperação de Senha
        
        Você solicitou a recuperação de sua senha no FovDark.
        
        Acesse o link abaixo para definir uma nova senha:
        {reset_url}
        
        Este link expira em 1 hora.
        
        Se você não solicitou esta recuperação, ignore este email.
        
        © 2024 FovDark
        """
        
        return send_email(email, "🔐 FovDark - Recuperação de Senha", html_content, text_content)
        
    except Exception as e:
        logger.error(f"Erro ao enviar email de recuperação: {e}")
        return False

def send_license_email(email: str, license_obj: License, product: Product) -> bool:
    """Enviar email com informações da licença"""
    try:
        # Template HTML
        html_template = """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Nova Licença - FovDark</title>
            <style>
                body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
                .container { max-width: 600px; margin: 0 auto; padding: 20px; }
                .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; text-align: center; }
                .content { background: #f8f9fa; padding: 30px; }
                .license-box { background: white; border: 2px solid #667eea; padding: 20px; margin: 20px 0; border-radius: 8px; }
                .license-key { font-family: monospace; font-size: 18px; font-weight: bold; color: #667eea; word-break: break-all; }
                .button { display: inline-block; background: #28a745; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; margin: 20px 0; }
                .footer { text-align: center; padding: 20px; color: #666; font-size: 12px; }
                .info-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 15px; margin: 20px 0; }
                .info-item { background: white; padding: 15px; border-radius: 5px; border-left: 4px solid #667eea; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🎉 Sua Licença Está Pronta!</h1>
                    <p>FovDark - Sistema de Licenças Digitais</p>
                </div>
                <div class="content">
                    <h2>Licença Ativada com Sucesso</h2>
                    <p>Parabéns! Sua compra foi processada e sua licença está ativa.</p>
                    
                    <div class="license-box">
                        <h3>🔑 Chave da Licença:</h3>
                        <div class="license-key">{{license_key}}</div>
                    </div>
                    
                    <div class="info-grid">
                        <div class="info-item">
                            <strong>📦 Produto:</strong><br>
                            {{product_name}}
                        </div>
                        <div class="info-item">
                            <strong>⏰ Válida até:</strong><br>
                            {{expires_at}}
                        </div>
                        <div class="info-item">
                            <strong>📊 Status:</strong><br>
                            <span style="color: #28a745;">{{status}}</span>
                        </div>
                        <div class="info-item">
                            <strong>📅 Ativada em:</strong><br>
                            {{created_at}}
                        </div>
                    </div>
                    
                    <h3>📋 Como usar sua licença:</h3>
                    <ol>
                        <li>Acesse seu painel no FovDark</li>
                        <li>Vá para a seção "Downloads"</li>
                        <li>Baixe o produto usando sua licença</li>
                        <li>Siga as instruções de instalação</li>
                    </ol>
                    
                    <p style="text-align: center;">
                        <a href="{{site_url}}/painel" class="button">🚀 Acessar Painel</a>
                    </p>
                    
                    <div style="background: #fff3cd; border: 1px solid #ffeaa7; padding: 15px; border-radius: 5px; margin: 20px 0;">
                        <h4>⚠️ Importante:</h4>
                        <ul>
                            <li>Guarde esta chave de licença em local seguro</li>
                            <li>A licença é vinculada ao seu dispositivo</li>
                            <li>Para suporte, entre em contato conosco</li>
                        </ul>
                    </div>
                </div>
                <div class="footer">
                    <p>© 2024 FovDark - Sistema de Licenças Digitais</p>
                    <p>Para suporte: support@fovdark.com</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        template = Template(html_template)
        html_content = template.render(
            license_key=license_obj.license_key,
            product_name=product.name,
            expires_at=license_obj.expires_at.strftime("%d/%m/%Y %H:%M"),
            status="ATIVA",
            created_at=license_obj.created_at.strftime("%d/%m/%Y %H:%M"),
            site_url=os.getenv('SITE_URL', 'http://localhost:5000')
        )
        
        # Conteúdo texto simples
        text_content = f"""
        FovDark - Nova Licença Ativada
        
        Sua compra foi processada e sua licença está ativa!
        
        Chave da Licença: {license_obj.license_key}
        
        Produto: {product.name}
        Válida até: {license_obj.expires_at.strftime("%d/%m/%Y %H:%M")}
        Status: ATIVA
        
        Acesse seu painel em: {os.getenv('SITE_URL', 'http://localhost:5000')}/painel
        
        © 2024 FovDark
        """
        
        return send_email(email, "🎉 Sua Licença FovDark Está Pronta!", html_content, text_content)
        
    except Exception as e:
        logger.error(f"Erro ao enviar email de licença: {e}")
        return False

def send_welcome_email(email: str, username: str) -> bool:
    """Enviar email de boas-vindas"""
    try:
        html_template = """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Bem-vindo ao FovDark</title>
            <style>
                body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
                .container { max-width: 600px; margin: 0 auto; padding: 20px; }
                .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; text-align: center; }
                .content { background: #f8f9fa; padding: 30px; }
                .button { display: inline-block; background: #667eea; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; margin: 20px 0; }
                .footer { text-align: center; padding: 20px; color: #666; font-size: 12px; }
                .feature-list { list-style: none; padding: 0; }
                .feature-list li { padding: 10px 0; border-bottom: 1px solid #eee; }
                .feature-list li:before { content: "✨ "; color: #667eea; font-weight: bold; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🎉 Bem-vindo ao FovDark!</h1>
                    <p>Sistema de Licenças Digitais</p>
                </div>
                <div class="content">
                    <h2>Olá, {{username}}!</h2>
                    <p>Seja bem-vindo ao FovDark, sua plataforma para licenças digitais!</p>
                    
                    <h3>🚀 O que você pode fazer:</h3>
                    <ul class="feature-list">
                        <li>Explorar nossa coleção de ISOs customizadas</li>
                        <li>Baixar programas e aplicativos otimizados</li>
                        <li>Acessar cheats e trainers para seus jogos</li>
                        <li>Encontrar mods exclusivos</li>
                        <li>Gerenciar suas licenças no painel pessoal</li>
                    </ul>
                    
                    <p style="text-align: center;">
                        <a href="{{site_url}}" class="button">🔍 Explorar Produtos</a>
                    </p>
                    
                    <div style="background: #d1ecf1; border: 1px solid #bee5eb; padding: 15px; border-radius: 5px; margin: 20px 0;">
                        <h4>💡 Dica:</h4>
                        <p>Mantenha suas licenças sempre ativas e aproveite nossos produtos exclusivos!</p>
                    </div>
                </div>
                <div class="footer">
                    <p>© 2024 FovDark - Sistema de Licenças Digitais</p>
                    <p>Para suporte: support@fovdark.com</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        template = Template(html_template)
        html_content = template.render(
            username=username,
            site_url=os.getenv('SITE_URL', 'http://localhost:5000')
        )
        
        text_content = f"""
        Bem-vindo ao FovDark!
        
        Olá, {username}!
        
        Seja bem-vindo ao FovDark, sua plataforma para licenças digitais!
        
        Explore nossa coleção de produtos em: {os.getenv('SITE_URL', 'http://localhost:5000')}
        
        © 2024 FovDark
        """
        
        return send_email(email, "🎉 Bem-vindo ao FovDark!", html_content, text_content)
        
    except Exception as e:
        logger.error(f"Erro ao enviar email de boas-vindas: {e}")
        return False

def send_license_expiry_warning(email: str, license_obj: License, product: Product, days_remaining: int) -> bool:
    """Enviar aviso de expiração de licença"""
    try:
        html_template = """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Licença Expirando - FovDark</title>
            <style>
                body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
                .container { max-width: 600px; margin: 0 auto; padding: 20px; }
                .header { background: linear-gradient(135deg, #f39c12 0%, #e74c3c 100%); color: white; padding: 20px; text-align: center; }
                .content { background: #f8f9fa; padding: 30px; }
                .warning-box { background: #fff3cd; border: 2px solid #ffc107; padding: 20px; margin: 20px 0; border-radius: 8px; }
                .button { display: inline-block; background: #e74c3c; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; margin: 20px 0; }
                .footer { text-align: center; padding: 20px; color: #666; font-size: 12px; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>⚠️ Licença Expirando!</h1>
                    <p>FovDark - Aviso Importante</p>
                </div>
                <div class="content">
                    <h2>Sua licença está prestes a expirar</h2>
                    
                    <div class="warning-box">
                        <h3>📦 Produto: {{product_name}}</h3>
                        <p><strong>🔑 Licença:</strong> {{license_key}}</p>
                        <p><strong>⏰ Expira em:</strong> {{days_remaining}} dias</p>
                        <p><strong>📅 Data de expiração:</strong> {{expires_at}}</p>
                    </div>
                    
                    <p>Renove sua licença agora para continuar aproveitando todos os benefícios!</p>
                    
                    <p style="text-align: center;">
                        <a href="{{site_url}}/products/{{product_id}}" class="button">🔄 Renovar Licença</a>
                    </p>
                </div>
                <div class="footer">
                    <p>© 2024 FovDark - Sistema de Licenças Digitais</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        template = Template(html_template)
        html_content = template.render(
            product_name=product.name,
            license_key=license_obj.license_key,
            days_remaining=days_remaining,
            expires_at=license_obj.expires_at.strftime("%d/%m/%Y %H:%M"),
            site_url=os.getenv('SITE_URL', 'http://localhost:5000'),
            product_id=product.id
        )
        
        return send_email(email, "⚠️ Licença Expirando - FovDark", html_content)
        
    except Exception as e:
        logger.error(f"Erro ao enviar aviso de expiração: {e}")
        return False

def test_email_configuration() -> bool:
    """Testar configuração de email"""
    try:
        # Tentar conectar ao servidor SMTP
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SMTP_USERNAME, SMTP_PASSWORD)
        server.quit()
        
        logger.info("Configuração de email testada com sucesso")
        return True
        
    except Exception as e:
        logger.error(f"Erro na configuração de email: {e}")
        return False
