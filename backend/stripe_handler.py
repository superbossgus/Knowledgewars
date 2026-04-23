"""
Stripe Checkout Handler
"""
from typing import Optional, Dict, Any, List
from pydantic import BaseModel
import stripe

class CheckoutSessionRequest(BaseModel):
    customer_email: str
    line_items: List[Dict[str, Any]]
    success_url: str
    cancel_url: str
    metadata: Optional[Dict[str, str]] = None

class CheckoutSessionResponse(BaseModel):
    id: str
    url: Optional[str] = None
    client_secret: Optional[str] = None
    status: str

class StripeCheckout:
    def __init__(self, api_key: str, webhook_url: str = ""):
        stripe.api_key = api_key
        self.webhook_url = webhook_url
    
    async def create_checkout_session(self, request: CheckoutSessionRequest) -> CheckoutSessionResponse:
        try:
            session = stripe.checkout.Session.create(
                customer_email=request.customer_email,
                payment_method_types=["card"],
                line_items=request.line_items,
                mode="payment",
                success_url=request.success_url,
                cancel_url=request.cancel_url,
                metadata=request.metadata or {},
            )
            return CheckoutSessionResponse(id=session.id, url=session.url, client_secret=session.client_secret, status=session.payment_status)
        except stripe.error.StripeError as e:
            raise Exception(f"Stripe error: {str(e)}")
