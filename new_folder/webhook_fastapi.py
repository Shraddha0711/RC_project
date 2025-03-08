from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import stripe
from firebase_admin import credentials, firestore, initialize_app
import os
from dotenv import load_dotenv

load_dotenv()

# Initialize Firebase
cred_path = os.getenv("CRED_PATH")
cred = credentials.Certificate(cred_path)
initialize_app(cred)
db = firestore.client()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Change to specific domain in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
endpoint_secret = os.getenv("STRIPE_ENDPOINT_SECRET")

@app.post("/webhook")
async def stripe_webhook(request: Request):
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, endpoint_secret)
    except stripe.error.SignatureVerificationError as e:
        raise HTTPException(status_code=400, detail="Webhook signature verification failed")

    # Handle successful payment
    if event["type"] == "payment_intent.succeeded":
        payment_intent = event["data"]["object"]
        handle_successful_payment(payment_intent)

    return {"status": "success"}

def handle_successful_payment(payment_intent):
    """Handles storing successful payment in Firestore"""
    amount_total = payment_intent["amount"]
    receipt_email = payment_intent.get("receipt_email", "unknown")

    # Save transaction to Firestore
    transaction_data = {
        "email": receipt_email,
        "amount": amount_total,
        "timestamp": firestore.SERVER_TIMESTAMP,
    }
    db.collection("transactions").add(transaction_data)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=9000)
