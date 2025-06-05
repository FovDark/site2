# FovDark Gaming - Digital Downloads & Licenses Platform

Uma plataforma moderna para downloads de software gaming e licenças digitais com estética cyberpunk.

## 🚀 Funcionalidades

### Homepage Gaming
- **Hero Section** com gradientes animados e estética cyberpunk
- **6 Categorias Gaming**: Softwares, ISOs Gamers, Otimizadores, Mods & Trainers, Cheats & Scripts, Suporte
- **Seção "Mais Baixados"** com 6 produtos populares (FovDark Optimizer, Windows 11 Gaming, etc.)
- **"Como Funciona"** em 3 passos com animações
- **Estatísticas Animadas** com contadores dinâmicos
- **Animações de Scroll** com Intersection Observer
- **Design Responsivo** para mobile

### Sistema Backend
- **Sistema de Usuários** com autenticação JWT
- **Gerenciamento de Produtos** com categorias
- **Sistema de Licenças** com HWID
- **Downloads Protegidos** por licença
- **Painel Administrativo** completo
- **Integração Supabase** PostgreSQL

## 🛠 Tecnologias

- **Backend**: FastAPI + Python 3.11
- **Database**: Supabase PostgreSQL
- **Frontend**: HTML5, CSS3, JavaScript (Vanilla)
- **Styling**: CSS Grid, Flexbox, Gradientes, Animações
- **Authentication**: JWT + bcrypt
- **ORM**: SQLAlchemy

## 📦 Configuração no Replit

### 1. Configuração do Supabase
1. Crie um projeto no [Supabase](https://supabase.com)
2. Vá em Settings > Database
3. Copie a Connection String (URI)
4. Cole no campo `DATABASE_URL` nos Secrets do Replit

### 2. Variáveis de Ambiente (Secrets)
Configure estas variáveis nos Secrets do Replit:

```bash
DATABASE_URL=postgresql://user:password@host:port/database
JWT_SECRET_KEY=seu-jwt-secret-aqui
SECRET_KEY=sua-flask-secret-key-aqui
ENVIRONMENT=production
```

### 3. Deploy Automático
O projeto está configurado para deploy automático no Replit com:
- Configurações de produção otimizadas
- Pool de conexões PostgreSQL configurado
- Middleware de segurança ativado
- Logs estruturados

## 🎮 Recursos Gaming

### Design Cyberpunk
- Paleta de cores neon (cyan, magenta, verde)
- Gradientes animados nos títulos
- Efeitos de hover com transformações
- Partículas flutuantes no hero
- Backdrop filters e glass morphism

### Animações Interativas
- Contadores animados nas estatísticas
- Cards com entrada em fade + slide up
- Hover effects nos botões e cards
- Parallax no hero section
- Ripple effects nos cliques

### Funcionalidades JavaScript
- Intersection Observer para performance
- Smooth scrolling para âncoras
- Animações baseadas em delay
- Touch enhancements para mobile
- Accessibility melhorada

## 📁 Estrutura do Projeto

```
fovdark/
├── main_simple.py          # Aplicação principal FastAPI
├── config.py               # Configurações centralizadas
├── database.py             # Conexão Supabase + SQLAlchemy
├── models.py               # Modelos do banco de dados
├── auth.py                 # Sistema de autenticação
├── templates/
│   ├── base.html          # Template base
│   ├── index.html         # Homepage gaming
│   ├── login.html         # Página de login
│   ├── register.html      # Página de registro
│   └── painel.html        # Painel do usuário
├── static/
│   ├── css/style.css      # Estilos principais
│   └── js/script.js       # JavaScript principal
└── README.md              # Este arquivo
```

## 🔧 Desenvolvimento Local

1. Clone o repositório
2. Configure as variáveis de ambiente
3. Execute:
```bash
python -m uvicorn main_simple:app --host 0.0.0.0 --port 5000 --reload
```

## 🚀 Deploy em Produção

O projeto está otimizado para Replit Deployments com:
- Configurações de segurança para produção
- Pool de conexões PostgreSQL otimizado
- CORS configurado para domínios Replit
- SSL/TLS habilitado para Supabase

### Dados Iniciais
O sistema cria automaticamente:
- **5 Categorias** padrão (ISOs Customizadas, Programas, Otimizadores, Cheats & Trainers, Mods)
- **Usuário Admin** (admin/admin123)

## 🎯 Próximos Passos

1. **Sistema de Pagamentos**: Integração com gateways
2. **Upload de Arquivos**: Sistema de downloads
3. **API REST**: Endpoints para aplicações externas
4. **Dashboard Analytics**: Métricas de downloads
5. **Sistema de Avaliações**: Reviews de produtos

## 📞 Suporte

Para suporte técnico ou dúvidas sobre implementação, consulte a documentação do projeto ou entre em contato através dos canais oficiais.

---

**FovDark Gaming** - Elevando sua experiência digital ao próximo nível! 🎮