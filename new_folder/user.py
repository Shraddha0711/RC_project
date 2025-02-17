from fastapi import FastAPI, HTTPException
import firebase_admin
from firebase_admin import credentials, firestore
from fastapi.middleware.cors import CORSMiddleware
import os

app = FastAPI()

# Initialize Firebase
cred = credentials.Certificate(os.getenv("FIREBASE_CREDENTIALS_PATH"))
firebase_admin.initialize_app(cred)
db = firestore.client()


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/users")
def get_all_users():
    """Fetch all users from Firestore"""
    try:
        users_ref = db.collection("users").stream()
        users = []

        for user in users_ref:
            user_data = user.to_dict()
            user_data["id"] = user.id  # Include document ID
            users.append(user_data)

        return {"users": users}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/sponsored-users")
def get_sponsored_users():
    """Fetch only users with sponsored.status = True"""
    try:
        users_ref = db.collection("users").where("sponsored.status", "==", True).stream()
        sponsored_users = []

        for user in users_ref:
            user_data = user.to_dict()
            user_data["id"] = user.id  # Include document ID
            sponsored_users.append(user_data)

        return {"sponsored_users": sponsored_users}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
