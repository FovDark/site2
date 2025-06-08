#!/usr/bin/env python3
"""
Script para criar um produto de teste e demonstrar a sincronização automática com Stripe
"""

import os
import sys
from datetime import datetime
from sqlalchemy.orm import Session

# Adicionar o diretório do projeto ao path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import get_db
from models import Product, Category
from stripe_product_sync import auto_sync_product_create

def create_test_product():
    """Criar produto de teste para demonstrar sincronização"""
    db = next(get_db())
    
    try:
        # Verificar se existe categoria
        category = db.query(Category).filter(Category.name == "Jogos").first()
        if not category:
            category = Category(
                name="Jogos",
                description="Categoria de jogos e aplicações gaming",
                icon="fa-gamepad",
                is_active=True
            )
            db.add(category)
            db.commit()
            db.refresh(category)
            print(f"✓ Categoria criada: {category.name}")
        
        # Criar produto de teste
        test_product = Product(
            name="FovDark Pro Gaming Tool",
            description="Ferramenta avançada para gamers profissionais com recursos exclusivos de otimização e análise.",
            price=29.99,
            category_id=category.id,
            duration_days=30,
            image_url="https://via.placeholder.com/400x300?text=FovDark+Pro",
            download_url="https://github.com/fovdark/pro/releases/latest",
            requirements="Windows 10/11, 8GB RAM, DirectX 12",
            tags="gaming,optimization,fps,performance",
            is_active=True,
            is_featured=True
        )
        
        db.add(test_product)
        db.commit()
        db.refresh(test_product)
        
        print(f"✓ Produto criado: {test_product.name} (ID: {test_product.id})")
        print(f"  Preço: R$ {test_product.price}")
        print(f"  Categoria: {category.name}")
        
        # Sincronizar automaticamente com Stripe
        print("\n🔄 Iniciando sincronização automática com Stripe...")
        sync_result = auto_sync_product_create(test_product, db)
        
        if sync_result.get('success'):
            print(f"✅ Sincronização bem-sucedida!")
            print(f"  Stripe Product ID: {sync_result.get('stripe_product_id')}")
            print(f"  Stripe Price ID: {sync_result.get('stripe_price_id')}")
        else:
            print(f"❌ Erro na sincronização: {sync_result.get('message')}")
            
        return test_product
        
    except Exception as e:
        print(f"❌ Erro ao criar produto: {str(e)}")
        db.rollback()
        return None
    finally:
        db.close()

if __name__ == "__main__":
    print("🚀 Criando produto de teste para demonstrar sincronização automática...")
    print("=" * 60)
    
    product = create_test_product()
    
    if product:
        print("\n✅ Demonstração concluída!")
        print("🔗 Acesse o painel administrativo para ver o produto sincronizado")
        print("💳 Os botões de pagamento agora direcionam automaticamente para o Stripe")
    else:
        print("\n❌ Falha na demonstração")