from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import stripe
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Change to specific domain in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Set your Stripe secret key
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

class PaymentRequest(BaseModel):
    amount: int  # Amount in cents (e.g., 5000 = $50)
    currency: str = "usd"

@app.post("/create-payment-intent")
async def create_payment_intent(data: PaymentRequest):
    try:
        # Create a PaymentIntent
        payment_intent = stripe.PaymentIntent.create(
            amount=data.amount,
            currency=data.currency,
            payment_method_types=["card"]
        )

        return {"clientSecret": payment_intent.client_secret}
    
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
