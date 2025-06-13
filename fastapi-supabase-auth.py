import re
"""
fastapi==0.104.1
uvicorn==0.24.0
python-jose[cryptography]==3.3.0
python-multipart==0.0.6
supabase==2.0.2
pydantic==2.5.0
python-dotenv==1.0.0
httpx==0.25.2
"""

# main.py
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import HTTPBearer
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, Dict, Any, List
from dotenv import load_dotenv
from supabase import create_client, Client
from datetime import datetime
import logging

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Supabase JWT Authentication API",
    description="Simple authentication system using Supabase and JWT tokens",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware - configure for your needs
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Supabase configuration
SUPABASE_ANON_KEY = ""
SUPABASE_URL = ""
SUPABASE_SERVICE_KEY = ""

# Initialize Supabase clients
supabase: Client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
supabase_admin: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

# Security
security = HTTPBearer()

# Pydantic models
class UserSignup(BaseModel):
    username: str = Field(..., min_length=3, max_length=50, description="Username must be 3-50 characters")
    password: str = Field(..., min_length=6, description="Password must be at least 6 characters")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)

class SIPScheme(BaseModel):
    user_id: str = Field(..., description="User ID for the SIP")
    scheme_name: str = Field(..., description="Name of the SIP scheme")
    monthly_amount: int = Field(..., description="Monthly investment amount")
    start_date: str = Field(..., description="Start date of the SIP in YYYY-MM-DD format")

class AuthResponse(BaseModel):
    message: str
    user_id: Optional[str] = None

class SchemeSummary(BaseModel):
    scheme_name: str
    total_investment: float
    months_invested: int

class SIPResponse(BaseModel):
    schemes: List[SchemeSummary]
    total_investment: float

# Helper functions
def generate_email_from_username(username: str) -> str:
    """Generate a fake email from username for Supabase compatibility"""
    # Remove any non-alphanumeric characters and convert to lowercase
    clean_username = re.sub(r'[^a-zA-Z0-9]', '', username.lower())
    return f"{clean_username}@gmail.com"

# Exception handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    logger.error(f"HTTP Exception: {exc.detail}")
    return {
        "error": exc.detail,
        "status_code": exc.status_code
    }

# Authentication endpoints
@app.post("/auth/signup", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def signup(user_data: UserSignup):
    """Sign up a new user"""
    try:
        response = supabase.auth.sign_up({
            "email": generate_email_from_username(user_data.username),
            "password": user_data.password,
            "options": {"data": user_data.metadata}
        })
        
        if response.user:
            logger.info(f"User created: {response.user.email}")
            return AuthResponse(
                message="User created successfully.",
                user_id=response.user.id
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to create user"
            )
            
    except Exception as e:
        logger.error(f"Signup error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@app.post("/auth/sip", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def create_sip(sip_data: SIPScheme):
    """Create a new SIP for a user"""
    try:
        # Get user session from user_id using admin client
        user_response = supabase_admin.auth.admin.get_user_by_id(sip_data.user_id)
        
        if not user_response.user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        # Store SIP details in Supabase using admin client
        response = supabase_admin.table("sips").insert({
            "user_id": sip_data.user_id,
            "scheme_name": sip_data.scheme_name,
            "monthly_amount": sip_data.monthly_amount,
            "start_date": sip_data.start_date
        }).execute()
        
        if response.data:
            logger.info(f"SIP created for user: {sip_data.user_id}")
            return AuthResponse(
                message="SIP created successfully.",
                user_id=sip_data.user_id
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to create SIP"
            )
            
    except Exception as e:
        logger.error(f"SIP creation error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@app.get("/auth/sips/summary/{user_id}", response_model=SIPResponse)
async def get_sips_summary(user_id: str):
    """Get all SIPs and total investment for a user"""
    try:
        # Verify user exists
        user_response = supabase_admin.auth.admin.get_user_by_id(user_id)
        
        if not user_response.user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        # Get all SIPs for the user
        response = supabase_admin.table("sips").select("*").eq("user_id", user_id).execute()
        
        if not response.data:
            return SIPResponse(schemes=[], total_investment=0)

        # Calculate investment details for each scheme
        scheme_details = {}
        current_date = datetime.now()
        total_investment = 0
        
        for sip in response.data:
            start_date = datetime.strptime(sip["start_date"], "%Y-%m-%d")
            months_diff = (current_date.year - start_date.year) * 12 + current_date.month - start_date.month
            scheme_investment = sip["monthly_amount"] * months_diff
            
            if sip["scheme_name"] not in scheme_details:
                scheme_details[sip["scheme_name"]] = {
                    "scheme_name": sip["scheme_name"],
                    "total_investment": 0,
                    "months_invested": months_diff
                }
            
            scheme_details[sip["scheme_name"]]["total_investment"] += scheme_investment
            total_investment += scheme_investment

        return SIPResponse(
            schemes=list(scheme_details.values()),
            total_investment=total_investment
        )
            
    except Exception as e:
        logger.error(f"Error fetching SIPs: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
