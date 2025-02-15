from fastapi import FastAPI, HTTPException, Depends, status, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
import firebase_admin
from firebase_admin import credentials, auth
from google.oauth2 import id_token
from google.auth.transport import requests
import json
import requests as http_requests
from typing import Optional
from config import settings
from models import *
from email_service import send_email

import os
from dotenv import load_dotenv
load_dotenv()

# Initialize Firebase
cred = credentials.Certificate(os.getenv("FIREBASE_CREDENTIALS_PATH"))
firebase_admin.initialize_app(cred)

app = FastAPI()

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Utility Functions
async def verify_firebase_token(token: str = Depends(oauth2_scheme)):
    try:
        decoded_token = auth.verify_id_token(token)
        return decoded_token
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

async def send_verification_email(user_id: str):
    try:
        user = auth.get_user(user_id)
        verification_link = auth.generate_email_verification_link(user.email)
        
        await send_email(
            to_email=user.email,
            subject="Verify your email",
            html_content=f"Click here to verify your email: {verification_link}"
        )
        
        return verification_link
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error sending verification email: {str(e)}"
        )

# Authentication Routes
@app.post("/auth/signup")
async def signup(user: UserSignUp, background_tasks: BackgroundTasks):
    # try:
        # Create user in Firebase
        user_record = auth.create_user(
            email=user.email,
            password=user.password,
            display_name=user.name,
            email_verified=False
        )
        
        # Update custom claims
        auth.set_custom_user_claims(user_record.uid, {
            "location": user.location,
            "phone": user.phone
        })
        
        # Send verification email
        background_tasks.add_task(send_verification_email, user_record.uid)
        
        # Create custom token
        custom_token = auth.create_custom_token(user_record.uid)
        
        return {
            "message": "User created successfully. Please check your email for verification.",
            "uid": user_record.uid,
            "token": custom_token
        }
    # except Exception as e:
    #     raise HTTPException(
    #         status_code=status.HTTP_400_BAD_REQUEST,
    #         detail=str(e)
    #     )

@app.post("/auth/signin")
async def signin(user: UserSignIn):
    try:
        user_record = auth.get_user_by_email(user.email)
        custom_token = auth.create_custom_token(user_record.uid)
        
        return {
            "message": "Login successful",
            "uid": user_record.uid,
            "token": custom_token,
            "email_verified": user_record.email_verified
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )

@app.post("/auth/forgot-password")
async def forgot_password(forgot_pwd: ForgotPassword, background_tasks: BackgroundTasks):
    try:
        reset_link = auth.generate_password_reset_link(forgot_pwd.email)
        
        background_tasks.add_task(
            send_email,
            to_email=forgot_pwd.email,
            subject="Reset your password",
            html_content=f"Click here to reset your password: {reset_link}"
        )
        
        return {"message": "Password reset link sent successfully"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error generating reset link: {str(e)}"
        )

@app.get("/auth/verify-email")
async def verify_email(token: str):
    try:
        decoded_token = auth.verify_id_token(token)
        user_id = decoded_token['uid']
        
        auth.update_user(
            user_id,
            email_verified=True
        )
        
        return {"message": "Email verified successfully"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error verifying email: {str(e)}"
        )

# OAuth Routes
@app.get("/auth/google/url")
async def google_auth_url():
    return {
        "url": f"https://accounts.google.com/o/oauth2/v2/auth?"
        f"client_id={settings.GOOGLE_CLIENT_ID}&"
        f"response_type=code&"
        f"scope=email profile&"
        f"redirect_uri={settings.GOOGLE_REDIRECT_URI}"
    }

@app.get("/auth/google/callback")
async def google_callback(code: str):
    try:
        # Exchange code for tokens
        token_url = "https://oauth2.googleapis.com/token"
        data = {
            "code": code,
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "redirect_uri": settings.GOOGLE_REDIRECT_URI,
            "grant_type": "authorization_code"
        }
        
        response = http_requests.post(token_url, data=data)
        tokens = response.json()
        
        # Verify ID token
        id_info = id_token.verify_oauth2_token(
            tokens["id_token"],
            requests.Request(),
            settings.GOOGLE_CLIENT_ID
        )
        
        # Create or update Firebase user
        try:
            user = auth.get_user_by_email(id_info["email"])
        except auth.UserNotFoundError:
            user = auth.create_user(
                email=id_info["email"],
                display_name=id_info.get("name"),
                photo_url=id_info.get("picture"),
                email_verified=True
            )
        
        custom_token = auth.create_custom_token(user.uid)
        
        return {
            "message": "Google authentication successful",
            "token": custom_token,
            "user": {
                "uid": user.uid,
                "email": user.email,
                "name": user.display_name
            }
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Google authentication failed: {str(e)}"
        )

@app.get("/auth/linkedin/url")
async def linkedin_auth_url():
    return {
        "url": f"https://www.linkedin.com/oauth/v2/authorization?"
        f"client_id={settings.LINKEDIN_CLIENT_ID}&"
        f"response_type=code&"
        f"scope=r_liteprofile r_emailaddress&"
        f"redirect_uri={settings.LINKEDIN_REDIRECT_URI}"
    }

@app.get("/auth/linkedin/callback")
async def linkedin_callback(code: str):
    try:
        # Exchange code for access token
        token_url = "https://www.linkedin.com/oauth/v2/accessToken"
        data = {
            "grant_type": "authorization_code",
            "code": code,
            "client_id": settings.LINKEDIN_CLIENT_ID,
            "client_secret": settings.LINKEDIN_CLIENT_SECRET,
            "redirect_uri": settings.LINKEDIN_REDIRECT_URI
        }
        
        response = http_requests.post(token_url, data=data)
        access_token = response.json()["access_token"]
        
        # Get user profile
        headers = {"Authorization": f"Bearer {access_token}"}
        profile_url = "https://api.linkedin.com/v2/me"
        email_url = "https://api.linkedin.com/v2/emailAddress?q=members&projection=(elements*(handle~))"
        
        profile = http_requests.get(profile_url, headers=headers).json()
        email_data = http_requests.get(email_url, headers=headers).json()
        email = email_data["elements"][0]["handle~"]["emailAddress"]
        
        try:
            user = auth.get_user_by_email(email)
        except auth.UserNotFoundError:
            user = auth.create_user(
                email=email,
                display_name=f"{profile.get('localizedFirstName', '')} {profile.get('localizedLastName', '')}",
                email_verified=True
            )
        
        custom_token = auth.create_custom_token(user.uid)
        
        return {
            "message": "LinkedIn authentication successful",
            "token": custom_token,
            "user": {
                "uid": user.uid,
                "email": user.email,
                "name": user.display_name
            }
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"LinkedIn authentication failed: {str(e)}"
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)