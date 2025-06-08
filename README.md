# FovDark Gaming - Sistema de Licenças Digitais

Uma plataforma completa para venda e gerenciamento de licenças digitais de software gaming.

## 🚀 Funcionalidades

### Para Usuários
- **Cadastro e Login** - Sistema de autenticação seguro
- **Catálogo de Produtos** - Navegação por categorias
- **Sistema de Pagamentos** - Integração com Infinite Pay
- **Downloads Seguros** - Acesso a produtos licenciados
- **Painel do Usuário** - Gerenciamento de licenças ativas

### Para Administradores
- **Painel Administrativo** - Dashboard com estatísticas
- **Gerenciamento de Produtos** - CRUD completo
- **Controle de Usuários** - Ativação/suspensão
- **Relatórios** - Analytics de vendas e licenças
- **Logs do Sistema** - Monitoramento de atividades

## 🛠️ Tecnologias

- **Backend:** FastAPI + Python 3.11
- **Banco de Dados:** PostgreSQL / SQLite
- **Frontend:** HTML5 + CSS3 + JavaScript
- **Autenticação:** JWT + BCrypt
- **Deploy:** Render / Docker
- **Pagamentos:** Infinite Pay

## 📦 Instalação Local

1. **Clone o repositório**
```bash
git clone <repository-url>
cd fovdark-gaming
```

2. **Crie ambiente virtual**
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate  # Windows
```

3. **Instale dependências**
```bash
pip install -r requirements.txt
```

4. **Configure variáveis de ambiente**
```bash
cp .env.example .env
# Edite o arquivo .env com suas configurações
```

5. **Execute a aplicação**
```bash
uvicorn main_simple:app --reload --host 0.0.0.0 --port 5000
```

## 🌐 Deploy no Render

### Configuração Rápida

1. **Fork este repositório**
2. **Conecte ao Render**
   - Acesse [render.com](https://render.com)
   - Conecte seu repositório GitHub
3. **Crie PostgreSQL Database**
   - New → PostgreSQL
   - Anote a connection string
4. **Crie Web Service**
   - New → Web Service
   - Build Command: `./build.sh`
   - Start Command: `gunicorn main_simple:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:$PORT`

### Variáveis de Ambiente Obrigatórias

```env
DATABASE_URL=postgresql://user:pass@host:port/db
JWT_SECRET_KEY=sua-chave-jwt-secreta
SECRET_KEY=sua-chave-secreta
ENVIRONMENT=production
DEBUG=false
ALLOWED_HOSTS=seudominio.onrender.com
CORS_ORIGINS=https://seudominio.onrender.com
```

## 🔧 Configuração Avançada

### Email (Opcional)
```env
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=seu-email@gmail.com
SMTP_PASSWORD=sua-senha-app
```

### Pagamentos (Opcional)
```env
INFINITE_PAY_API_KEY=sua-chave-api
INFINITE_PAY_WEBHOOK_SECRET=seu-webhook-secret
```

## 📁 Estrutura do Projeto

```
├── main_simple.py         # Aplicação principal
├── models.py             # Modelos do banco
├── database.py           # Configuração DB
├── auth.py              # Autenticação
├── config.py            # Configurações
├── admin.py             # Funções admin
├── license.py           # Sistema de licenças
├── static/              # CSS, JS, imagens
├── templates/           # Templates HTML
├── requirements.txt     # Dependências
├── render.yaml         # Config Render
├── Dockerfile          # Container
└── deploy_guide.md     # Guia detalhado
```

## 🚦 Status do Sistema

- ✅ Autenticação de usuários
- ✅ Sistema de produtos e categorias
- ✅ Gerenciamento de licenças
- ✅ Painel administrativo
- ✅ Interface responsiva
- ✅ Pronto para deploy
- ✅ Sistema de pagamentos
- ✅ Envio de emails

## 🔒 Segurança

- Rate limiting integrado
- Headers de segurança
- Validação de entrada
- Criptografia de senhas
- Tokens JWT seguros
- CORS configurado

## 📞 Suporte

Para dúvidas sobre deploy ou configuração, consulte:
- `deploy_guide.md` - Guia completo de deploy
- `.env.example` - Exemplo de configurações
- Logs do Render - Para debug em produção

## 📄 Licença

Projeto proprietário - FovDark Gaming