from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from .routes import router, ws_router
from .auth import create_access_token, verify_token
from dotenv import load_dotenv
import os

load_dotenv()

app = FastAPI(title="Geelark Automation API", version="1.0.0")

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- 1. TOKEN GENERATION ENDPOINT ---
# We need a schema for the request
class TokenRequest(BaseModel):
    client_name: str
    admin_secret: str # Simple protection for generation

@app.post("/generate-token")
def generate_token(request: TokenRequest):
    """
    Generates a 30-day JWT token. 
    Requires a hardcoded ADMIN_SECRET to prevent abuse.
    """
    MASTER_PASSWORD = os.getenv("ADMIN_PASSWORD")
    
    if request.admin_secret != MASTER_PASSWORD:
        raise HTTPException(status_code=403, detail="Invalid Admin Secret")
    
    # Create the token
    access_token = create_access_token(data={"sub": request.client_name})
    
    return {
        "access_token": access_token, 
        "token_type": "bearer",
        "expires_in_days": 30
    }

# --- 2. PROTECT THE MAIN ROUTER ---
# We add `dependencies=[Depends(verify_token)]`
# This effectively locks EVERY endpoint in router.py
app.include_router(router, dependencies=[Depends(verify_token)])
app.include_router(ws_router)

@app.get("/")
def root():
    return {"message": "Geelark Automation API is running (Protected)"}
