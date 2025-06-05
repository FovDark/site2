import os
import requests
import json
import hashlib
import hmac
from datetime import datetime
from typing import Dict, Optional
from sqlalchemy.orm import Session
from models import Transaction, License, User, Product
from license import create_license
from email_utils import send_license_email
import logging

# Configurações do Infinite Pay
INFINITE_PAY_API_KEY = os.getenv("INFINITE_PAY_API_KEY", "your_infinite_pay_api_key")
INFINITE_PAY_BASE_URL = os.getenv("INFINITE_PAY_BASE_URL", "https://api.infinitepay.io/v2")
INFINITE_PAY_WEBHOOK_SECRET = os.getenv("INFINITE_PAY_WEBHOOK_SECRET", "your_webhook_secret")

def create_payment(product: Product, user: User, hwid: str) -> Dict:
    """Criar pagamento no Infinite Pay"""
    try:
        payment_data = {
            "amount": int(product.price * 100),  # Valor em centavos
            "currency": "BRL",
            "customer": {
                "name": user.username,
                "email": user.email,
                "document": "00000000000"  # CPF fictício - ajustar conforme necessário
            },
            "description": f"Licença para {product.name}",
            "metadata": {
                "user_id": str(user.id),
                "product_id": str(product.id),
                "hwid": hwid
            },
            "notification_url": f"https://fovdark.com/api/webhook/payment",
            "return_url": f"https://fovdark.com/painel?payment=success",
            "cancel_url": f"https://fovdark.com/product/{product.id}?payment=cancelled"
        }
        
        headers = {
            "Authorization": f"Bearer {INFINITE_PAY_API_KEY}",
            "Content-Type": "application/json"
        }
        
        # Fazer requisição para API do Infinite Pay
        response = requests.post(
            f"{INFINITE_PAY_BASE_URL}/charges",
            json=payment_data,
            headers=headers,
            timeout=30
        )
        
        if response.status_code == 201:
            payment_response = response.json()
            logging.info(f"Payment created: {payment_response.get('id')} for user {user.id}")
            
            return {
                "success": True,
                "payment_id": payment_response.get("id"),
                "payment_url": payment_response.get("checkout_url"),
                "status": payment_response.get("status")
            }
        else:
            logging.error(f"Payment creation failed: {response.status_code} - {response.text}")
            return {
                "success": False,
                "error": "Erro ao criar pagamento",
                "details": response.text
            }
            
    except requests.exceptions.RequestException as e:
        logging.error(f"Payment API error: {e}")
        return {
            "success": False,
            "error": "Erro de conexão com gateway de pagamento"
        }
    except Exception as e:
        logging.error(f"Payment creation error: {e}")
        return {
            "success": False,
            "error": "Erro interno ao processar pagamento"
        }

def verify_payment_webhook(webhook_data: dict, db: Session) -> Dict:
    """Verificar e processar webhook de pagamento"""
    try:
        # Verificar assinatura do webhook (se configurada)
        if INFINITE_PAY_WEBHOOK_SECRET:
            signature = webhook_data.get("signature")
            if not verify_webhook_signature(webhook_data, signature):
                logging.warning("Invalid webhook signature")
                return {"success": False, "error": "Invalid signature"}
        
        # Extrair dados do webhook
        payment_id = webhook_data.get("id")
        status = webhook_data.get("status")
        metadata = webhook_data.get("metadata", {})
        
        if not payment_id:
            return {"success": False, "error": "Missing payment ID"}
        
        # Buscar transação
        transaction = db.query(Transaction).filter(
            Transaction.payment_id == payment_id
        ).first()
        
        if not transaction:
            logging.warning(f"Transaction not found for payment ID: {payment_id}")
            return {"success": False, "error": "Transaction not found"}
        
        # Processar status do pagamento
        if status == "paid" or status == "approved":
            return process_successful_payment(transaction, webhook_data, db)
        elif status == "failed" or status == "cancelled":
            return process_failed_payment(transaction, webhook_data, db)
        else:
            # Status intermediário, apenas atualizar
            transaction.status = "pending"
            transaction.gateway_response = json.dumps(webhook_data)
            db.commit()
            
            return {"success": True, "status": "pending"}
            
    except Exception as e:
        logging.error(f"Webhook processing error: {e}")
        return {"success": False, "error": str(e)}

def process_successful_payment(transaction: Transaction, webhook_data: dict, db: Session) -> Dict:
    """Processar pagamento aprovado"""
    try:
        # Atualizar transação
        transaction.status = "completed"
        transaction.completed_at = datetime.utcnow()
        transaction.gateway_response = json.dumps(webhook_data)
        
        # Extrair metadados
        metadata = webhook_data.get("metadata", {})
        hwid = metadata.get("hwid", "")
        
        # Crear licença
        license_obj = create_license(
            db=db,
            user_id=transaction.user_id,
            product_id=transaction.product_id,
            hwid=hwid,
            duration_days=30  # Duração padrão
        )
        
        db.commit()
        
        # Enviar email com licença
        user = transaction.user
        product = transaction.product
        
        expires_str = license_obj.expires_at.strftime("%d/%m/%Y") if license_obj.expires_at else "Sem expiração"
        
        send_license_email(
            to_email=user.email,
            username=user.username,
            product_name=product.name,
            license_key=license_obj.license_key,
            expires_at=expires_str
        )
        
        logging.info(f"Payment processed successfully: {transaction.id}")
        
        return {
            "success": True,
            "transaction_id": transaction.id,
            "user_id": transaction.user_id,
            "license_key": license_obj.license_key
        }
        
    except Exception as e:
        logging.error(f"Process successful payment error: {e}")
        db.rollback()
        return {"success": False, "error": str(e)}

def process_failed_payment(transaction: Transaction, webhook_data: dict, db: Session) -> Dict:
    """Processar pagamento falhado"""
    try:
        transaction.status = "failed"
        transaction.gateway_response = json.dumps(webhook_data)
        
        db.commit()
        
        logging.info(f"Payment failed: {transaction.id}")
        
        return {
            "success": True,
            "transaction_id": transaction.id,
            "status": "failed"
        }
        
    except Exception as e:
        logging.error(f"Process failed payment error: {e}")
        db.rollback()
        return {"success": False, "error": str(e)}

def verify_webhook_signature(webhook_data: dict, signature: str) -> bool:
    """Verificar assinatura do webhook"""
    try:
        if not INFINITE_PAY_WEBHOOK_SECRET or not signature:
            return True  # Pular verificação se não configurado
        
        # Criar payload para verificação
        payload = json.dumps(webhook_data, sort_keys=True, separators=(',', ':'))
        
        # Calcular HMAC
        calculated_signature = hmac.new(
            INFINITE_PAY_WEBHOOK_SECRET.encode(),
            payload.encode(),
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(signature, calculated_signature)
        
    except Exception as e:
        logging.error(f"Webhook signature verification error: {e}")
        return False

def get_payment_status(payment_id: str) -> Dict:
    """Consultar status do pagamento"""
    try:
        headers = {
            "Authorization": f"Bearer {INFINITE_PAY_API_KEY}",
            "Content-Type": "application/json"
        }
        
        response = requests.get(
            f"{INFINITE_PAY_BASE_URL}/charges/{payment_id}",
            headers=headers,
            timeout=30
        )
        
        if response.status_code == 200:
            return {
                "success": True,
                "data": response.json()
            }
        else:
            return {
                "success": False,
                "error": f"API Error: {response.status_code}"
            }
            
    except Exception as e:
        logging.error(f"Get payment status error: {e}")
        return {"success": False, "error": str(e)}

def refund_payment(payment_id: str, amount: Optional[float] = None) -> Dict:
    """Estornar pagamento"""
    try:
        refund_data = {}
        if amount:
            refund_data["amount"] = int(amount * 100)  # Valor em centavos
        
        headers = {
            "Authorization": f"Bearer {INFINITE_PAY_API_KEY}",
            "Content-Type": "application/json"
        }
        
        response = requests.post(
            f"{INFINITE_PAY_BASE_URL}/charges/{payment_id}/refund",
            json=refund_data,
            headers=headers,
            timeout=30
        )
        
        if response.status_code == 200:
            logging.info(f"Payment refunded: {payment_id}")
            return {
                "success": True,
                "data": response.json()
            }
        else:
            return {
                "success": False,
                "error": f"Refund failed: {response.status_code}"
            }
            
    except Exception as e:
        logging.error(f"Refund payment error: {e}")
        return {"success": False, "error": str(e)}

def cancel_payment(payment_id: str) -> Dict:
    """Cancelar pagamento"""
    try:
        headers = {
            "Authorization": f"Bearer {INFINITE_PAY_API_KEY}",
            "Content-Type": "application/json"
        }
        
        response = requests.delete(
            f"{INFINITE_PAY_BASE_URL}/charges/{payment_id}",
            headers=headers,
            timeout=30
        )
        
        if response.status_code == 200:
            logging.info(f"Payment cancelled: {payment_id}")
            return {
                "success": True,
                "data": response.json()
            }
        else:
            return {
                "success": False,
                "error": f"Cancel failed: {response.status_code}"
            }
            
    except Exception as e:
        logging.error(f"Cancel payment error: {e}")
        return {"success": False, "error": str(e)}

def get_transaction_report(db: Session, start_date: datetime, end_date: datetime) -> Dict:
    """Gerar relatório de transações"""
    try:
        transactions = db.query(Transaction).filter(
            Transaction.created_at >= start_date,
            Transaction.created_at <= end_date
        ).all()
        
        total_transactions = len(transactions)
        completed_transactions = [t for t in transactions if t.status == "completed"]
        total_revenue = sum(t.amount for t in completed_transactions)
        
        return {
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat()
            },
            "summary": {
                "total_transactions": total_transactions,
                "completed_transactions": len(completed_transactions),
                "total_revenue": round(total_revenue, 2),
                "average_ticket": round(total_revenue / len(completed_transactions), 2) if completed_transactions else 0
            },
            "transactions": [
                {
                    "id": t.id,
                    "user_id": t.user_id,
                    "product_name": t.product.name if t.product else "N/A",
                    "amount": t.amount,
                    "status": t.status,
                    "created_at": t.created_at.isoformat(),
                    "completed_at": t.completed_at.isoformat() if t.completed_at else None
                }
                for t in transactions
            ]
        }
        
    except Exception as e:
        logging.error(f"Transaction report error: {e}")
        return {"error": str(e)}
