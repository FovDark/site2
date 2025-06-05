-- FovDark Gaming Database Schema for Supabase
-- Execute this SQL in your Supabase SQL Editor

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Users table
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    is_active BOOLEAN DEFAULT true,
    is_admin BOOLEAN DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_login TIMESTAMP WITH TIME ZONE,
    
    -- Indexes
    CONSTRAINT users_username_key UNIQUE (username),
    CONSTRAINT users_email_key UNIQUE (email)
);

-- Categories table
CREATE TABLE categories (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    description TEXT,
    icon VARCHAR(50), -- Font Awesome icon class
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    CONSTRAINT categories_name_key UNIQUE (name)
);

-- Products table
CREATE TABLE products (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    price DECIMAL(10,2) NOT NULL DEFAULT 0,
    category_id INTEGER NOT NULL REFERENCES categories(id) ON DELETE CASCADE,
    duration_days INTEGER DEFAULT 30,
    image_url VARCHAR(500),
    download_url VARCHAR(500),
    requirements TEXT,
    tags VARCHAR(500),
    is_active BOOLEAN DEFAULT true,
    is_featured BOOLEAN DEFAULT false,
    download_count INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Licenses table
CREATE TABLE licenses (
    id SERIAL PRIMARY KEY,
    license_key VARCHAR(255) UNIQUE NOT NULL DEFAULT upper(replace(cast(uuid_generate_v4() as text), '-', '')),
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    hwid VARCHAR(255),
    status VARCHAR(20) DEFAULT 'active', -- active, expired, suspended
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    last_verified TIMESTAMP WITH TIME ZONE,
    
    CONSTRAINT licenses_license_key_key UNIQUE (license_key)
);

-- Transactions table
CREATE TABLE transactions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    amount DECIMAL(10,2) NOT NULL,
    payment_id VARCHAR(255) UNIQUE,
    payment_method VARCHAR(50),
    status VARCHAR(20) DEFAULT 'pending', -- pending, approved, rejected, expired
    gateway_response JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    CONSTRAINT transactions_payment_id_key UNIQUE (payment_id)
);

-- Downloads table
CREATE TABLE downloads (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    license_id INTEGER NOT NULL REFERENCES licenses(id) ON DELETE CASCADE,
    ip_address INET,
    user_agent TEXT,
    downloaded_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Security logs table
CREATE TABLE security_logs (
    id SERIAL PRIMARY KEY,
    event_type VARCHAR(50) NOT NULL,
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    ip_address INET,
    user_agent TEXT,
    details JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Password resets table
CREATE TABLE password_resets (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token VARCHAR(255) UNIQUE NOT NULL DEFAULT replace(cast(uuid_generate_v4() as text), '-', ''),
    expires_at TIMESTAMP WITH TIME ZONE DEFAULT (NOW() + INTERVAL '1 hour'),
    is_used BOOLEAN DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    CONSTRAINT password_resets_token_key UNIQUE (token)
);

-- Create indexes for better performance
CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_is_active ON users(is_active);

CREATE INDEX idx_products_category_id ON products(category_id);
CREATE INDEX idx_products_is_active ON products(is_active);
CREATE INDEX idx_products_is_featured ON products(is_featured);
CREATE INDEX idx_products_created_at ON products(created_at);

CREATE INDEX idx_licenses_user_id ON licenses(user_id);
CREATE INDEX idx_licenses_product_id ON licenses(product_id);
CREATE INDEX idx_licenses_status ON licenses(status);
CREATE INDEX idx_licenses_expires_at ON licenses(expires_at);
CREATE INDEX idx_licenses_license_key ON licenses(license_key);

CREATE INDEX idx_transactions_user_id ON transactions(user_id);
CREATE INDEX idx_transactions_product_id ON transactions(product_id);
CREATE INDEX idx_transactions_status ON transactions(status);
CREATE INDEX idx_transactions_payment_id ON transactions(payment_id);

CREATE INDEX idx_downloads_user_id ON downloads(user_id);
CREATE INDEX idx_downloads_product_id ON downloads(product_id);
CREATE INDEX idx_downloads_license_id ON downloads(license_id);
CREATE INDEX idx_downloads_downloaded_at ON downloads(downloaded_at);

CREATE INDEX idx_security_logs_user_id ON security_logs(user_id);
CREATE INDEX idx_security_logs_event_type ON security_logs(event_type);
CREATE INDEX idx_security_logs_created_at ON security_logs(created_at);

-- Create triggers for updated_at timestamps
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_products_updated_at BEFORE UPDATE ON products
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_transactions_updated_at BEFORE UPDATE ON transactions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Insert default categories
INSERT INTO categories (name, description, icon) VALUES 
('Software', 'Programas e aplicativos diversos', 'fa-laptop-code'),
('ISOs', 'Imagens de sistemas operacionais', 'fa-compact-disc'),
('Otimizadores', 'Ferramentas de otimização de sistema', 'fa-tachometer-alt'),
('Mods & Trainers', 'Modificações e trainers para jogos', 'fa-gamepad'),
('Cheats & Scripts', 'Scripts e cheats para gaming', 'fa-code'),
('Utilitários', 'Ferramentas úteis do sistema', 'fa-tools'),
('Segurança', 'Antivírus e proteção', 'fa-shield-alt'),
('Multimedia', 'Editores de vídeo e áudio', 'fa-photo-video');

-- Insert sample products
INSERT INTO products (name, description, price, category_id, duration_days, image_url, download_url, requirements, tags, is_featured) VALUES 
('System Optimizer Pro', 'Otimizador completo para Windows com limpeza de registro, desfragmentação e aceleração do sistema.', 29.90, 3, 30, 'https://via.placeholder.com/300x200/667eea/ffffff?text=System+Optimizer', 'https://example.com/downloads/system-optimizer.zip', 'Windows 10/11, 4GB RAM, 500MB espaço livre', 'otimização, limpeza, registro, performance', true),

('Game Booster Ultimate', 'Acelere seus jogos com otimização automática de recursos e modo gaming dedicado.', 19.90, 4, 60, 'https://via.placeholder.com/300x200/10b981/ffffff?text=Game+Booster', 'https://example.com/downloads/game-booster.zip', 'Windows 10/11, 8GB RAM', 'gaming, performance, fps, otimização', true),

('Windows 11 Pro ISO', 'Imagem oficial do Windows 11 Professional para instalação limpa.', 0.00, 2, 365, 'https://via.placeholder.com/300x200/3b82f6/ffffff?text=Windows+11', 'https://example.com/downloads/win11-pro.iso', 'TPM 2.0, Secure Boot, 8GB RAM', 'windows, iso, sistema operacional, gratuito', false),

('Advanced Registry Cleaner', 'Ferramenta avançada para limpeza e otimização do registro do Windows.', 15.90, 6, 30, 'https://via.placeholder.com/300x200/f59e0b/ffffff?text=Registry+Cleaner', 'https://example.com/downloads/registry-cleaner.zip', 'Windows 7/8/10/11, 2GB RAM', 'registro, limpeza, otimização, windows', false),

('AntiVirus Pro Security', 'Proteção completa contra malware, vírus e ameaças online.', 39.90, 7, 90, 'https://via.placeholder.com/300x200/dc2626/ffffff?text=AntiVirus+Pro', 'https://example.com/downloads/antivirus-pro.zip', 'Windows 10/11, 4GB RAM, Conexão com internet', 'antivirus, segurança, proteção, malware', true),

('Video Editor Ultimate', 'Editor de vídeo profissional com efeitos avançados e renderização 4K.', 49.90, 8, 60, 'https://via.placeholder.com/300x200/8b5cf6/ffffff?text=Video+Editor', 'https://example.com/downloads/video-editor.zip', 'Windows 10/11, 16GB RAM, Placa de vídeo dedicada', 'vídeo, edição, 4k, profissional', true);

-- Create an admin user (password is 'admin123' hashed with bcrypt)
-- Note: You should change this password in production
INSERT INTO users (username, email, password_hash, is_admin) VALUES 
('admin', 'admin@fovdark.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewMhfcKmXPg6/jdW', true);

-- Create a regular test user (password is 'user123')
INSERT INTO users (username, email, password_hash, is_admin) VALUES 
('testuser', 'user@fovdark.com', '$2b$12$XkTFcWy.5BYeFZQ2O7.Fn.kZcJ3sYFwYlKUPjNhNF8K2O6XYF8gqm', false);

-- Create sample licenses for the test user
INSERT INTO licenses (user_id, product_id, expires_at, status) VALUES 
(2, 1, NOW() + INTERVAL '30 days', 'active'),
(2, 2, NOW() + INTERVAL '60 days', 'active'),
(2, 3, NOW() + INTERVAL '365 days', 'active');

-- Create sample transactions
INSERT INTO transactions (user_id, product_id, amount, payment_id, status) VALUES 
(2, 1, 29.90, 'PAY001', 'approved'),
(2, 2, 19.90, 'PAY002', 'approved'),
(2, 3, 0.00, 'FREE001', 'approved');

-- Create sample downloads
INSERT INTO downloads (user_id, product_id, license_id, ip_address) VALUES 
(2, 1, 1, '192.168.1.100'),
(2, 2, 2, '192.168.1.100'),
(2, 3, 3, '192.168.1.100');

-- Enable Row Level Security (RLS) for better security
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE licenses ENABLE ROW LEVEL SECURITY;
ALTER TABLE transactions ENABLE ROW LEVEL SECURITY;
ALTER TABLE downloads ENABLE ROW LEVEL SECURITY;

-- Create RLS policies
CREATE POLICY "Users can view own data" ON users FOR SELECT USING (auth.uid()::text = id::text);
CREATE POLICY "Users can update own data" ON users FOR UPDATE USING (auth.uid()::text = id::text);

CREATE POLICY "Users can view own licenses" ON licenses FOR SELECT USING (auth.uid()::text = user_id::text);
CREATE POLICY "Users can view own transactions" ON transactions FOR SELECT USING (auth.uid()::text = user_id::text);
CREATE POLICY "Users can view own downloads" ON downloads FOR SELECT USING (auth.uid()::text = user_id::text);

-- Grant permissions for public access (you might want to restrict this in production)
GRANT USAGE ON SCHEMA public TO postgres, anon, authenticated, service_role;
GRANT ALL ON ALL TABLES IN SCHEMA public TO postgres, anon, authenticated, service_role;
GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO postgres, anon, authenticated, service_role;
GRANT ALL ON ALL FUNCTIONS IN SCHEMA public TO postgres, anon, authenticated, service_role;

-- Create views for common queries
CREATE VIEW active_licenses_view AS
SELECT 
    l.*,
    u.username,
    u.email,
    p.name as product_name,
    p.category_id,
    c.name as category_name
FROM licenses l
JOIN users u ON l.user_id = u.id
JOIN products p ON l.product_id = p.id
JOIN categories c ON p.category_id = c.id
WHERE l.status = 'active' AND l.expires_at > NOW();

CREATE VIEW user_stats_view AS
SELECT 
    u.id,
    u.username,
    u.email,
    u.created_at,
    COUNT(DISTINCT l.id) as total_licenses,
    COUNT(DISTINCT CASE WHEN l.status = 'active' AND l.expires_at > NOW() THEN l.id END) as active_licenses,
    COUNT(DISTINCT t.id) as total_transactions,
    COUNT(DISTINCT d.id) as total_downloads,
    COALESCE(SUM(CASE WHEN t.status = 'approved' THEN t.amount ELSE 0 END), 0) as total_spent
FROM users u
LEFT JOIN licenses l ON u.id = l.user_id
LEFT JOIN transactions t ON u.id = t.user_id
LEFT JOIN downloads d ON u.id = d.user_id
GROUP BY u.id, u.username, u.email, u.created_at;

-- Create function to automatically expire licenses
CREATE OR REPLACE FUNCTION expire_old_licenses()
RETURNS void AS $$
BEGIN
    UPDATE licenses 
    SET status = 'expired' 
    WHERE expires_at <= NOW() AND status = 'active';
END;
$$ LANGUAGE plpgsql;

-- Create function to get user dashboard data
CREATE OR REPLACE FUNCTION get_user_dashboard(user_id_param INTEGER)
RETURNS JSON AS $$
DECLARE
    result JSON;
BEGIN
    SELECT json_build_object(
        'user_info', (
            SELECT json_build_object(
                'id', id,
                'username', username,
                'email', email,
                'is_admin', is_admin,
                'created_at', created_at
            )
            FROM users WHERE id = user_id_param
        ),
        'stats', (
            SELECT json_build_object(
                'active_licenses', COUNT(DISTINCT CASE WHEN l.status = 'active' AND l.expires_at > NOW() THEN l.id END),
                'total_downloads', COUNT(DISTINCT d.id),
                'total_transactions', COUNT(DISTINCT t.id),
                'expiring_licenses', COUNT(DISTINCT CASE WHEN l.status = 'active' AND l.expires_at <= NOW() + INTERVAL '7 days' THEN l.id END)
            )
            FROM licenses l
            LEFT JOIN downloads d ON l.user_id = d.user_id
            LEFT JOIN transactions t ON l.user_id = t.user_id
            WHERE l.user_id = user_id_param
        ),
        'recent_licenses', (
            SELECT COALESCE(json_agg(
                json_build_object(
                    'id', l.id,
                    'license_key', l.license_key,
                    'product_name', p.name,
                    'category_name', c.name,
                    'status', l.status,
                    'expires_at', l.expires_at,
                    'created_at', l.created_at,
                    'days_remaining', EXTRACT(days FROM l.expires_at - NOW())
                )
            ), '[]'::json)
            FROM licenses l
            JOIN products p ON l.product_id = p.id
            JOIN categories c ON p.category_id = c.id
            WHERE l.user_id = user_id_param
            ORDER BY l.created_at DESC
            LIMIT 5
        )
    ) INTO result;
    
    RETURN result;
END;
$$ LANGUAGE plpgsql;