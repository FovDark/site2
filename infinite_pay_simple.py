"""
Infinite Pay - Integração por Link Simples
Sistema simplificado para gerar links de pagamento
"""
import os
from datetime import datetime
from urllib.parse import urlencode
import logging

logger = logging.getLogger(__name__)

class InfinitePayLinkGenerator:
    """Gerador de links de pagamento Infinite Pay"""
    
    def __init__(self):
        self.base_url = "https://app.infinitepay.io"
        self.user_id = os.getenv("INFINITE_PAY_USER_ID", "")
        
    def create_payment_link(self, amount: float, description: str, user_id: int, product_id: int) -> dict:
        """Criar link de pagamento"""
        try:
            # Referência única para rastreamento
            reference = f"fovdark_user{user_id}_prod{product_id}_{int(datetime.now().timestamp())}"
            
            # Site base para retornos
            site_url = os.getenv("SITE_URL", "https://your-repl-name.replit.app")
            
            # Parâmetros do pagamento
            params = {
                "amount": f"{amount:.2f}".replace(".", ","),
                "description": description[:100],  # Limite de caracteres
                "reference": reference,
                "success_url": f"{site_url}/payment/success?ref={reference}",
                "cancel_url": f"{site_url}/payment/cancel?ref={reference}",
                "pending_url": f"{site_url}/payment/pending?ref={reference}"
            }
            
            # Construir URL do link
            if self.user_id:
                payment_url = f"{self.base_url}/pay/{self.user_id}?" + urlencode(params)
            else:
                # URL genérica para testes
                payment_url = f"{self.base_url}/pay?" + urlencode(params)
            
            return {
                "success": True,
                "payment_url": payment_url,
                "reference": reference,
                "amount": amount,
                "description": description
            }
            
        except Exception as e:
            logger.error(f"Erro ao gerar link de pagamento: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def format_currency(self, amount: float) -> str:
        """Formatar valor em reais"""
        return f"R$ {amount:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

# Instância global
infinite_pay = InfinitePayLinkGenerator()

def create_payment_link(amount: float, description: str, user_id: int, product_id: int) -> dict:
    """Função wrapper para criar link de pagamento"""
    return infinite_pay.create_payment_link(amount, description, user_id, product_id)

def format_price(amount: float) -> str:
    """Formatar preço em reais"""
    return infinite_pay.format_currency(amount)