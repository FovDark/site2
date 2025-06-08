-- Migração para Supabase
-- Execute este SQL no painel do Supabase

-- 1. Criar tabela de usuários compatível
CREATE TABLE IF NOT EXISTS public.users (
  id SERIAL NOT NULL,
  email CHARACTER VARYING NOT NULL,
  senha_hash CHARACTER VARYING NOT NULL,
  data_expiracao TIMESTAMP WITHOUT TIME ZONE NULL,
  is_admin BOOLEAN NULL DEFAULT false,
  created_at TIMESTAMP WITHOUT TIME ZONE NULL DEFAULT NOW(),
  updated_at TIMESTAMP WITHOUT TIME ZONE NULL DEFAULT NOW(),
  hwid TEXT NULL,
  status_licenca CHARACTER VARYING NULL DEFAULT 'pendente',
  tentativas_login INTEGER NULL DEFAULT 0,
  ultimo_login TIMESTAMP WITHOUT TIME ZONE NULL,
  ip_registro CHARACTER VARYING NULL,
  ip_ultimo_login CHARACTER VARYING NULL,
  CONSTRAINT users_pkey PRIMARY KEY (id)
);

-- Índices para performance
CREATE UNIQUE INDEX IF NOT EXISTS ix_users_email ON public.users USING btree (email);
CREATE INDEX IF NOT EXISTS ix_users_id ON public.users USING btree (id);

-- 2. Criar tabela de categorias
CREATE TABLE IF NOT EXISTS public.categories (
  id SERIAL NOT NULL,
  name CHARACTER VARYING(100) NOT NULL UNIQUE,
  description TEXT,
  icon CHARACTER VARYING(50),
  is_active BOOLEAN DEFAULT true,
  created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
  CONSTRAINT categories_pkey PRIMARY KEY (id)
);

-- 3. Criar tabela de produtos
CREATE TABLE IF NOT EXISTS public.products (
  id SERIAL NOT NULL,
  name CHARACTER VARYING(255) NOT NULL,
  description TEXT,
  price DECIMAL(10,2) NOT NULL,
  category_id INTEGER NOT NULL,
  duration_days INTEGER DEFAULT 30,
  download_url CHARACTER VARYING(500),
  requirements TEXT,
  tags CHARACTER VARYING(500),
  image_url CHARACTER VARYING(500),
  is_active BOOLEAN DEFAULT true,
  created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
  CONSTRAINT products_pkey PRIMARY KEY (id),
  CONSTRAINT products_category_fkey FOREIGN KEY (category_id) REFERENCES categories(id)
);

-- 4. Criar tabela de licenças
CREATE TABLE IF NOT EXISTS public.licenses (
  id SERIAL NOT NULL,
  license_key CHARACTER VARYING(255) NOT NULL UNIQUE,
  user_id INTEGER NOT NULL,
  product_id INTEGER NOT NULL,
  hwid CHARACTER VARYING(255),
  expires_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
  is_active BOOLEAN DEFAULT true,
  created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
  last_used TIMESTAMP WITHOUT TIME ZONE,
  uses_count INTEGER DEFAULT 0,
  max_uses INTEGER DEFAULT 1,
  CONSTRAINT licenses_pkey PRIMARY KEY (id),
  CONSTRAINT licenses_user_fkey FOREIGN KEY (user_id) REFERENCES users(id),
  CONSTRAINT licenses_product_fkey FOREIGN KEY (product_id) REFERENCES products(id)
);

-- 5. Criar tabela de transações
CREATE TABLE IF NOT EXISTS public.transactions (
  id SERIAL NOT NULL,
  user_id INTEGER NOT NULL,
  product_id INTEGER NOT NULL,
  amount DECIMAL(10,2) NOT NULL,
  payment_method CHARACTER VARYING(50),
  payment_id CHARACTER VARYING(255),
  status CHARACTER VARYING(50) DEFAULT 'pending',
  created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
  completed_at TIMESTAMP WITHOUT TIME ZONE,
  CONSTRAINT transactions_pkey PRIMARY KEY (id),
  CONSTRAINT transactions_user_fkey FOREIGN KEY (user_id) REFERENCES users(id),
  CONSTRAINT transactions_product_fkey FOREIGN KEY (product_id) REFERENCES products(id)
);

-- 6. Criar tabela de downloads
CREATE TABLE IF NOT EXISTS public.downloads (
  id SERIAL NOT NULL,
  user_id INTEGER NOT NULL,
  product_id INTEGER NOT NULL,
  download_url CHARACTER VARYING(500),
  downloaded_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
  ip_address CHARACTER VARYING(45),
  user_agent TEXT,
  CONSTRAINT downloads_pkey PRIMARY KEY (id),
  CONSTRAINT downloads_user_fkey FOREIGN KEY (user_id) REFERENCES users(id),
  CONSTRAINT downloads_product_fkey FOREIGN KEY (product_id) REFERENCES products(id)
);

-- 7. Inserir categorias padrão
INSERT INTO public.categories (name, description, icon) VALUES
('ISOs Customizadas', 'Sistemas operacionais personalizados e otimizados', 'fa-compact-disc'),
('Hacks & Cheats', 'Ferramentas e modificações para jogos', 'fa-code'),
('Software Premium', 'Programas e aplicativos profissionais', 'fa-desktop'),
('Tools & Utilities', 'Utilitários e ferramentas diversas', 'fa-tools'),
('Games & Mods', 'Jogos e modificações', 'fa-gamepad')
ON CONFLICT (name) DO NOTHING;

-- 8. Inserir usuário admin padrão
-- Senha: admin123 (hash bcrypt)
INSERT INTO public.users (email, senha_hash, is_admin, status_licenca, tentativas_login) VALUES
('admin@fovdark.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LeZLOqy1OIIVS3YIa', true, 'ativo', 0)
ON CONFLICT (email) DO NOTHING;

-- 9. Criar função para atualizar updated_at automaticamente
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 10. Criar triggers para atualização automática
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_products_updated_at BEFORE UPDATE ON products
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();