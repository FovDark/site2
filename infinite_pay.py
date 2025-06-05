import os
import requests
import hashlib
import hmac
import json
from datetime import datetime
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

# Configurações do Infinite Pay
INFINITE_PAY_API_URL = os.getenv("INFINITE_PAY_API_URL", "https://api.infinitepay.io")
INFINITE_PAY_API_KEY = os.getenv("INFINITE_PAY_API_KEY", "")
INFINITE_PAY_SECRET = os.getenv("INFINITE_PAY_SECRET", "")
INFINITE_PAY_WEBHOOK_SECRET = os.getenv("INFINITE_PAY_WEBHOOK_SECRET", "")

class InfinitePayAPI:
    """Cliente para API do Infinite Pay"""
    
    def __init__(self):
        self.api_url = INFINITE_PAY_API_URL
        self.api_key = INFINITE_PAY_API_KEY
        self.secret = INFINITE_PAY_SECRET
        self.webhook_secret = INFINITE_PAY_WEBHOOK_SECRET
        
        if not self.api_key or not self.secret:
            logger.warning("Configurações do Infinite Pay não encontradas")
    
    def _make_request(self, method: str, endpoint: str, data: dict = None) -> dict:
        """Fazer requisição para API"""
        try:
            url = f"{self.api_url}{endpoint}"
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            response = requests.request(
                method=method,
                url=url,
                headers=headers,
                json=data,
                timeout=30
            )
            
            response.raise_for_status()
            return response.json()
            
        except requests.RequestException as e:
            logger.error(f"Erro na requisição Infinite Pay: {e}")
            return {"error": str(e)}
        except Exception as e:
            logger.error(f"Erro inesperado Infinite Pay: {e}")
            return {"error": str(e)}
    
    def create_payment(self, amount: float, description: str, user_id: int, product_id: int, **kwargs) -> dict:
        """Criar pagamento no Infinite Pay"""
        try:
            payment_data = {
                "amount": int(amount * 100),  # Converter para centavos
                "currency": "BRL",
                "description": description,
                "external_reference": f"user_{user_id}_product_{product_id}_{int(datetime.now().timestamp())}",
                "payment_method_types": ["credit_card", "debit_card", "pix", "boleto"],
                "success_url": f"{os.getenv('SITE_URL', 'http://localhost:5000')}/payment/success",
                "cancel_url": f"{os.getenv('SITE_URL', 'http://localhost:5000')}/payment/cancel",
                "webhook_url": f"{os.getenv('SITE_URL', 'http://localhost:5000')}/api/webhook/infinite-pay",
                "metadata": {
                    "user_id": user_id,
                    "product_id": product_id,
                    **kwargs
                }
            }
            
            response = self._make_request("POST", "/payments", payment_data)
            
            if "error" in response:
                return {"success": False, "error": response["error"]}
            
            return {
                "success": True,
                "payment_id": response.get("id"),
                "payment_url": response.get("checkout_url"),
                "status": response.get("status"),
                "external_reference": payment_data["external_reference"]
            }
            
        except Exception as e:
            logger.error(f"Erro ao criar pagamento: {e}")
            return {"success": False, "error": str(e)}
    
    def get_payment(self, payment_id: str) -> dict:
        """Obter detalhes do pagamento"""
        try:
            response = self._make_request("GET", f"/payments/{payment_id}")
            
            if "error" in response:
                return {"success": False, "error": response["error"]}
            
            return {
                "success": True,
                "payment": response
            }
            
        except Exception as e:
            logger.error(f"Erro ao obter pagamento {payment_id}: {e}")
            return {"success": False, "error": str(e)}
    
    def verify_webhook_signature(self, payload: bytes, signature: str) -> bool:
        """Verificar assinatura do webhook"""
        try:
            if not self.webhook_secret:
                logger.warning("Webhook secret não configurado")
                return False
            
            expected_signature = hmac.new(
                self.webhook_secret.encode(),
                payload,
                hashlib.sha256
            ).hexdigest()
            
            return hmac.compare_digest(signature, expected_signature)
            
        except Exception as e:
            logger.error(f"Erro ao verificar assinatura webhook: {e}")
            return False
    
    def process_webhook(self, payload: dict, signature: str = None) -> dict:
        """Processar webhook do Infinite Pay"""
        try:
            # Verificar assinatura se fornecida
            if signature:
                payload_bytes = json.dumps(payload, sort_keys=True).encode()
                if not self.verify_webhook_signature(payload_bytes, signature):
                    return {"success": False, "error": "Assinatura inválida"}
            
            event_type = payload.get("event_type")
            payment_data = payload.get("data", {})
            
            if event_type == "payment.approved":
                return self._handle_payment_approved(payment_data)
            elif event_type == "payment.rejected":
                return self._handle_payment_rejected(payment_data)
            elif event_type == "payment.cancelled":
                return self._handle_payment_cancelled(payment_data)
            elif event_type == "payment.expired":
                return self._handle_payment_expired(payment_data)
            else:
                logger.warning(f"Evento webhook não reconhecido: {event_type}")
                return {"success": True, "message": "Evento ignorado"}
            
        except Exception as e:
            logger.error(f"Erro ao processar webhook: {e}")
            return {"success": False, "error": str(e)}
    
    def _handle_payment_approved(self, payment_data: dict) -> dict:
        """Processar pagamento aprovado"""
        try:
            payment_id = payment_data.get("id")
            logger.info(f"Pagamento aprovado: {payment_id}")
            
            return {
                "success": True,
                "status": "approved",
                "payment_id": payment_id,
                "metadata": payment_data.get("metadata", {})
            }
            
        except Exception as e:
            logger.error(f"Erro ao processar pagamento aprovado: {e}")
            return {"success": False, "error": str(e)}
    
    def _handle_payment_rejected(self, payment_data: dict) -> dict:
        """Processar pagamento rejeitado"""
        try:
            payment_id = payment_data.get("id")
            logger.warning(f"Pagamento rejeitado: {payment_id}")
            
            return {
                "success": True,
                "status": "rejected",
                "payment_id": payment_id,
                "metadata": payment_data.get("metadata", {})
            }
            
        except Exception as e:
            logger.error(f"Erro ao processar pagamento rejeitado: {e}")
            return {"success": False, "error": str(e)}
    
    def _handle_payment_cancelled(self, payment_data: dict) -> dict:
        """Processar pagamento cancelado"""
        try:
            payment_id = payment_data.get("id")
            logger.info(f"Pagamento cancelado: {payment_id}")
            
            return {
                "success": True,
                "status": "cancelled",
                "payment_id": payment_id,
                "metadata": payment_data.get("metadata", {})
            }
            
        except Exception as e:
            logger.error(f"Erro ao processar pagamento cancelado: {e}")
            return {"success": False, "error": str(e)}
    
    def _handle_payment_expired(self, payment_data: dict) -> dict:
        """Processar pagamento expirado"""
        try:
            payment_id = payment_data.get("id")
            logger.info(f"Pagamento expirado: {payment_id}")
            
            return {
                "success": True,
                "status": "expired",
                "payment_id": payment_id,
                "metadata": payment_data.get("metadata", {})
            }
            
        except Exception as e:
            logger.error(f"Erro ao processar pagamento expirado: {e}")
            return {"success": False, "error": str(e)}

# Instância global da API
infinite_pay_client = InfinitePayAPI()

def create_payment(amount: float, description: str, user_id: int, product_id: int, **kwargs) -> dict:
    """Criar pagamento (função wrapper)"""
    return infinite_pay_client.create_payment(amount, description, user_id, product_id, **kwargs)

def get_payment(payment_id: str) -> dict:
    """Obter pagamento (função wrapper)"""
    return infinite_pay_client.get_payment(payment_id)

def verify_payment_webhook(payload: dict, signature: str = None) -> dict:
    """Verificar webhook (função wrapper)"""
    return infinite_pay_client.process_webhook(payload, signature)

def test_infinite_pay_connection() -> bool:
    """Testar conexão com Infinite Pay"""
    try:
        if not INFINITE_PAY_API_KEY:
            logger.error("API Key do Infinite Pay não configurada")
            return False
        
        # Tentar fazer uma requisição simples para testar a conexão
        response = requests.get(
            f"{INFINITE_PAY_API_URL}/health",
            headers={"Authorization": f"Bearer {INFINITE_PAY_API_KEY}"},
            timeout=10
        )
        
        if response.status_code == 200:
            logger.info("Conexão com Infinite Pay OK")
            return True
        else:
            logger.warning(f"Infinite Pay retornou status: {response.status_code}")
            return False
            
    except requests.RequestException as e:
        logger.error(f"Erro na conexão com Infinite Pay: {e}")
        return False
    except Exception as e:
        logger.error(f"Erro inesperado ao testar Infinite Pay: {e}")
        return False

def format_currency(amount: float) -> str:
    """Formatar valor monetário"""
    return f"R$ {amount:.2f}".replace(".", ",")

def parse_currency(value: str) -> float:
    """Converter string monetária para float"""
    try:
        # Remover símbolos e converter
        cleaned = value.replace("R$", "").replace(".", "").replace(",", ".").strip()
        return float(cleaned)
    except:
        return 0.0
