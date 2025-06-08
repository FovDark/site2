# Guia de Deploy no Render

## Pré-requisitos
1. Conta no Render (https://render.com)
2. Repositório Git com o código da aplicação

## Configuração das Variáveis de Ambiente

No painel do Render, configure as seguintes variáveis de ambiente:

### Obrigatórias
```
DATABASE_URL=postgresql://user:password@hostname:port/database
JWT_SECRET_KEY=sua-chave-secreta-jwt-aqui
SECRET_KEY=sua-chave-secreta-flask-aqui
ENVIRONMENT=production
DEBUG=false
```

### Configurações de Rede
```
ALLOWED_HOSTS=seudominio.onrender.com,localhost,127.0.0.1
CORS_ORIGINS=https://seudominio.onrender.com
```

### Configurações de Email (Opcional)
```
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=seu-email@gmail.com
SMTP_PASSWORD=sua-senha-email
```

### Configurações de Pagamento (Opcional)
```
INFINITE_PAY_API_KEY=sua-chave-api-infinite-pay
INFINITE_PAY_WEBHOOK_SECRET=seu-webhook-secret
```

## Passos para Deploy

### 1. Criar Banco de Dados PostgreSQL
- No dashboard do Render, clique em "New" → "PostgreSQL"
- Configure nome e região
- Anote as credenciais de conexão

### 2. Criar Web Service
- No dashboard do Render, clique em "New" → "Web Service"
- Conecte seu repositório Git
- Configure as seguintes opções:

**Build Settings:**
- Build Command: `./build.sh`
- Start Command: `gunicorn main_simple:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:$PORT`

**Environment:**
- Runtime: Python 3
- Python Version: 3.11.10

### 3. Configurar Variáveis de Ambiente
- Adicione todas as variáveis listadas acima
- Para DATABASE_URL, use a string de conexão do PostgreSQL criado

### 4. Deploy
- Clique em "Create Web Service"
- O Render fará o build e deploy automaticamente

## Estrutura de Arquivos Criada

```
├── requirements.txt      # Dependências Python
├── runtime.txt          # Versão do Python
├── Procfile            # Comando de inicialização (Heroku)
├── render.yaml         # Configuração do Render
├── build.sh           # Script de build
├── Dockerfile         # Para containerização
├── .env.example       # Exemplo de variáveis de ambiente
└── deploy_guide.md    # Este guia
```

## Verificação de Funcionamento

Após o deploy, verifique:
1. ✅ Aplicação carrega sem erros
2. ✅ Banco de dados conecta corretamente
3. ✅ Autenticação funciona
4. ✅ Upload de arquivos funciona
5. ✅ Emails são enviados (se configurado)

## Solução de Problemas

### Erro de Conexão com Banco
- Verifique se DATABASE_URL está correto
- Certifique-se que o PostgreSQL está ativo

### Erro 500 Internal Server Error
- Verifique os logs no dashboard do Render
- Confirme se todas as variáveis obrigatórias estão configuradas

### Problemas com Arquivos Estáticos
- Os arquivos CSS/JS são servidos pela própria aplicação
- Verifique se a pasta /static existe

## URLs Importantes

- **Dashboard Render:** https://dashboard.render.com
- **Documentação:** https://render.com/docs
- **Status:** https://status.render.com

## Comandos Úteis

```bash
# Testar localmente com Gunicorn
gunicorn main_simple:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:5000

# Verificar dependências
pip freeze > requirements.txt

# Testar build script
./build.sh
```