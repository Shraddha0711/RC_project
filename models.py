from pydantic import BaseModel, EmailStr
from typing import Optional

class UserSignUp(BaseModel):
    email: EmailStr
    password: str
    name: str
    location: str
    phone: str

class UserSignIn(BaseModel):
    email: EmailStr
    password: str

class SSOSignIn(BaseModel):
    token: str
    provider: str

class ForgotPassword(BaseModel):
    email: EmailStr

class VerifyEmail(BaseModel):
    token: str