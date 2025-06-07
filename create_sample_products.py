"""
Script para criar produtos de exemplo em todas as categorias
"""
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from database import get_db
from models import Product, Category, User
import os

# Configuração do banco
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./fovdark.db")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def create_sample_products():
    """Criar produtos de exemplo"""
    db = SessionLocal()
    
    try:
        # Verificar se as categorias existem
        categories = {
            "Programas": db.query(Category).filter(Category.name == "Programas").first(),
            "Cheats & Trainers": db.query(Category).filter(Category.name == "Cheats & Trainers").first(),
            "Mods": db.query(Category).filter(Category.name == "Mods").first(),
            "ISOs Customizadas": db.query(Category).filter(Category.name == "ISOs Customizadas").first(),
            "Otimizadores": db.query(Category).filter(Category.name == "Otimizadores").first()
        }
        
        # Criar categorias se não existirem
        for cat_name, cat_obj in categories.items():
            if not cat_obj:
                icons = {
                    "Programas": "fas fa-desktop",
                    "Cheats & Trainers": "fas fa-gamepad",
                    "Mods": "fas fa-puzzle-piece",
                    "ISOs Customizadas": "fas fa-compact-disc",
                    "Otimizadores": "fas fa-tachometer-alt"
                }
                
                new_category = Category(
                    name=cat_name,
                    description=f"Categoria para {cat_name}",
                    icon=icons[cat_name],
                    is_active=True
                )
                db.add(new_category)
                db.commit()
                categories[cat_name] = new_category
        
        # Produtos de exemplo
        sample_products = [
            # PROGRAMAS
            {
                "name": "Adobe Creative Suite 2024 Pro",
                "description": "Pacote completo Adobe Creative Suite 2024 com Photoshop, Illustrator, After Effects, Premiere Pro e mais. Versão profissional completa com todas as funcionalidades desbloqueadas. Ideal para designers, editores de vídeo e criadores de conteúdo.",
                "price": 89.90,
                "category": "Programas",
                "duration_days": 365,
                "requirements": "Windows 10/11 64-bit, 8GB RAM mínimo (16GB recomendado), 20GB espaço livre, DirectX 12 compatível",
                "tags": "Adobe, Creative, Design, Photoshop, Illustrator, Premium",
                "is_featured": True
            },
            {
                "name": "Microsoft Office 2024 Professional",
                "description": "Pacote Microsoft Office 2024 completo incluindo Word, Excel, PowerPoint, Outlook, Access e Publisher. Versão profissional com todas as funcionalidades premium ativadas.",
                "price": 45.00,
                "category": "Programas",
                "duration_days": 365,
                "requirements": "Windows 10/11, 4GB RAM, 4GB espaço livre",
                "tags": "Microsoft, Office, Word, Excel, PowerPoint, Produtividade"
            },
            {
                "name": "IDM - Internet Download Manager Pro",
                "description": "Gerenciador de downloads mais rápido e eficiente. Acelera downloads em até 5x, suporte para todos os navegadores, organizador automático de arquivos.",
                "price": 0.00,
                "category": "Programas",
                "duration_days": 30,
                "requirements": "Windows 7/8/10/11, 512MB RAM",
                "tags": "Download, Gratuito, Velocidade, Internet"
            },
            {
                "name": "AutoCAD 2024 Professional",
                "description": "Software de CAD profissional para arquitetura, engenharia e design. Versão completa com todas as bibliotecas e ferramentas avançadas.",
                "price": 120.00,
                "category": "Programas",
                "duration_days": 180,
                "requirements": "Windows 10/11 64-bit, 8GB RAM, placa gráfica dedicada",
                "tags": "CAD, Arquitetura, Engenharia, Design, AutoCAD"
            },
            
            # CHEATS & TRAINERS
            {
                "name": "GTA V Online Mod Menu Premium",
                "description": "Mod menu completo para GTA V Online com proteções anti-ban, spawner de veículos, dinheiro infinito, teleporte e mais de 200 opções. Atualizado constantemente.",
                "price": 35.90,
                "category": "Cheats & Trainers",
                "duration_days": 30,
                "requirements": "GTA V versão mais recente, Windows 10/11",
                "tags": "GTA V, Mod Menu, Online, Dinheiro, Anti-Ban",
                "is_featured": True
            },
            {
                "name": "CS2 Aimbot & Wallhack Undetected",
                "description": "Cheat premium para Counter-Strike 2 com aimbot suave, wallhack, ESP, trigger bot e proteções anti-VAC. Sistema de atualização automática.",
                "price": 29.90,
                "category": "Cheats & Trainers",
                "duration_days": 30,
                "requirements": "Counter-Strike 2, Windows 10/11",
                "tags": "CS2, Aimbot, Wallhack, Undetected, VAC-Safe"
            },
            {
                "name": "Minecraft Hack Client",
                "description": "Cliente de hack para Minecraft com X-Ray, Fly, Speed hack, Auto mine e mais de 100 módulos. Compatível com servidores principais.",
                "price": 0.00,
                "category": "Cheats & Trainers",
                "duration_days": 7,
                "requirements": "Minecraft Java Edition, Windows/Linux/Mac",
                "tags": "Minecraft, Hack Client, X-Ray, Gratuito"
            },
            {
                "name": "Apex Legends Aimbot Pro",
                "description": "Aimbot profissional para Apex Legends com configurações personalizáveis, ESP de inimigos, prediction avançada e sistema anti-detecção.",
                "price": 42.00,
                "category": "Cheats & Trainers",
                "duration_days": 30,
                "requirements": "Apex Legends, Windows 10/11, 8GB RAM",
                "tags": "Apex Legends, Aimbot, ESP, Battle Royale"
            },
            
            # MODS
            {
                "name": "Skyrim Enhanced Graphics Pack",
                "description": "Pacote completo de mods gráficos para Skyrim com texturas 4K, iluminação realista, efeitos climáticos e mais de 150 mods visuais integrados.",
                "price": 25.50,
                "category": "Mods",
                "duration_days": 90,
                "requirements": "The Elder Scrolls V: Skyrim Special Edition, 16GB RAM, GTX 1060 ou superior",
                "tags": "Skyrim, Gráficos, 4K, Texturas, Visual"
            },
            {
                "name": "GTA San Andreas Modern Pack",
                "description": "Mod pack que moderniza completamente GTA San Andreas com gráficos atuais, novos carros, armas, missões extras e sistema de física realista.",
                "price": 18.90,
                "category": "Mods",
                "duration_days": 60,
                "requirements": "GTA San Andreas original, 4GB RAM",
                "tags": "GTA SA, Modernização, Gráficos, Carros"
            },
            {
                "name": "Minecraft Shaders Pack",
                "description": "Pacote de shaders premium para Minecraft com iluminação realista, reflexos, sombras dinâmicas e efeitos de água. Compatível com Optifine.",
                "price": 0.00,
                "category": "Mods",
                "duration_days": 30,
                "requirements": "Minecraft + Optifine, placa gráfica dedicada",
                "tags": "Minecraft, Shaders, Gráficos, Gratuito, Optifine"
            },
            {
                "name": "Cyberpunk 2077 Gameplay Overhaul",
                "description": "Mod que reequilibra completamente Cyberpunk 2077 com novo sistema de combate, IA melhorada, economia balanceada e correções de bugs.",
                "price": 32.00,
                "category": "Mods",
                "duration_days": 120,
                "requirements": "Cyberpunk 2077, todas as DLCs, 16GB RAM",
                "tags": "Cyberpunk 2077, Gameplay, IA, Rebalanceamento"
            },
            
            # ISOs CUSTOMIZADAS
            {
                "name": "Windows 11 Pro Gaming Edition",
                "description": "Windows 11 Pro customizado especialmente para gamers com otimizações de performance, drivers pre-instalados, software gaming e tweaks avançados.",
                "price": 55.00,
                "category": "ISOs Customizadas",
                "duration_days": 365,
                "requirements": "TPM 2.0, UEFI, 8GB RAM, 64GB armazenamento",
                "tags": "Windows 11, Gaming, Otimizado, Performance",
                "is_featured": True
            },
            {
                "name": "Ubuntu Linux Gaming Distro",
                "description": "Distribuição Ubuntu customizada para jogos com Steam, Lutris, Wine configurado, drivers gráficos e emuladores pre-instalados.",
                "price": 0.00,
                "category": "ISOs Customizadas",
                "duration_days": 0,
                "requirements": "4GB RAM, 25GB espaço livre, suporte UEFI",
                "tags": "Ubuntu, Linux, Gaming, Steam, Gratuito"
            },
            {
                "name": "Windows 10 LTSC Developer Edition",
                "description": "Windows 10 LTSC customizado para desenvolvedores com Visual Studio, ferramentas de desenvolvimento, ambientes configurados e otimizações.",
                "price": 38.90,
                "category": "ISOs Customizadas",
                "duration_days": 180,
                "requirements": "4GB RAM, 32GB armazenamento, processador 64-bit",
                "tags": "Windows 10, LTSC, Desenvolvimento, Visual Studio"
            },
            
            # OTIMIZADORES
            {
                "name": "PC Optimizer Pro 2024",
                "description": "Otimizador completo de PC com limpeza de registro, desfragmentação inteligente, otimização de startup, limpeza de arquivos temporários e boost de gaming.",
                "price": 28.50,
                "category": "Otimizadores",
                "duration_days": 365,
                "requirements": "Windows 7/8/10/11, 2GB RAM",
                "tags": "Otimização, Performance, Limpeza, Registro"
            },
            {
                "name": "Gaming Booster Ultimate",
                "description": "Software especializado em otimização para jogos. Fecha processos desnecessários, otimiza RAM, prioriza recursos para jogos e monitora temperatura.",
                "price": 22.90,
                "category": "Otimizadores",
                "duration_days": 180,
                "requirements": "Windows 10/11, 4GB RAM",
                "tags": "Gaming, Performance, RAM, CPU, Otimização"
            },
            {
                "name": "System Cleaner Lite",
                "description": "Limpador básico de sistema com remoção de arquivos temporários, cache de navegadores e limpeza básica de registro. Versão gratuita.",
                "price": 0.00,
                "category": "Otimizadores",
                "duration_days": 30,
                "requirements": "Windows 7/8/10/11, 1GB RAM",
                "tags": "Limpeza, Gratuito, Temporários, Cache"
            },
            {
                "name": "RAM Optimizer Pro",
                "description": "Otimizador especializado em memória RAM com compressão inteligente, limpeza automática, monitoramento em tempo real e alertas de uso.",
                "price": 15.00,
                "category": "Otimizadores",
                "duration_days": 90,
                "requirements": "Windows 8/10/11, 4GB RAM mínimo",
                "tags": "RAM, Memória, Monitoramento, Otimização"
            }
        ]
        
        # Criar produtos
        for product_data in sample_products:
            category = categories[product_data["category"]]
            
            # Verificar se produto já existe
            existing = db.query(Product).filter(Product.name == product_data["name"]).first()
            if existing:
                continue
            
            product = Product(
                name=product_data["name"],
                description=product_data["description"],
                price=product_data["price"],
                category_id=category.id,
                duration_days=product_data["duration_days"],
                requirements=product_data["requirements"],
                tags=product_data["tags"],
                is_active=True,
                is_featured=product_data.get("is_featured", False)
            )
            
            db.add(product)
        
        db.commit()
        print("Produtos de exemplo criados com sucesso!")
        
        # Mostrar estatísticas
        for cat_name, category in categories.items():
            count = db.query(Product).filter(Product.category_id == category.id).count()
            print(f"{cat_name}: {count} produtos")
    
    except Exception as e:
        print(f"Erro ao criar produtos: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    create_sample_products()