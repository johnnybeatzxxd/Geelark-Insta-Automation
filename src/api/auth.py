import os
from datetime import datetime, timedelta
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from dotenv import load_dotenv

load_dotenv()

# --- CONFIGURATION ---
# In production, put this in your .env file!
# Run: openssl rand -hex 32  <-- to generate a good key
SECRET_KEY = os.getenv("SECRET_KEY", "CHANGE_THIS_TO_A_REALLY_LONG_RANDOM_STRING")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_DAYS = 30

# This tells FastAPI where to look for the token (the URL is just for docs)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def create_access_token(data: dict):
    """
    Creates a JWT token that expires in 30 days.
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS)
    
    # We hide the expiry date inside the token claims
    to_encode.update({"exp": expire})
    
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        client_id: str = payload.get("sub")
        if client_id is None:
            raise HTTPException(status_code=401, detail="Invalid token payload")
        return client_id
        
    except ExpiredSignatureError:
        # Specific error for time-out
        raise HTTPException(
            status_code=401, 
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except JWTError:
        # Catch-all for fake/tampered tokens
        raise HTTPException(
            status_code=401, 
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )
