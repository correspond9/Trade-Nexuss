"""
Credentials Router
Handles credential management endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from pydantic import BaseModel, Field

from app.database import get_db
from app.dependencies import get_current_active_user
from app.services.credentials_service import credentials_service

router = APIRouter()

# Pydantic models for request/response
class CredentialsCreate(BaseModel):
    auth_mode: str = Field(..., description="Authentication mode: DAILY_TOKEN or STATIC_IP")
    client_id: Optional[str] = Field(None, description="Client ID for Daily Token mode")
    access_token: Optional[str] = Field(None, description="Access token for Daily Token mode")
    api_key: Optional[str] = Field(None, description="API key for Static IP mode")
    client_secret: Optional[str] = Field(None, description="Client secret for Static IP mode")
    is_default: bool = Field(True, description="Set as default credentials")

class CredentialsResponse(BaseModel):
    id: int
    auth_mode: str
    client_id: Optional[str]
    access_token: Optional[str]
    api_key: Optional[str]
    client_secret: Optional[str]
    is_default: bool
    created_at: Optional[str]
    last_used_at: Optional[str]

class ModeSwitchRequest(BaseModel):
    auth_mode: str = Field(..., description="Authentication mode to switch to")

@router.get("/", response_model=List[CredentialsResponse])
async def get_credentials(
    auth_mode: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """Get user credentials - temporarily no auth for testing"""
    try:
        # Mock user ID for testing - replace with actual auth later
        user_id = 1
        
        if auth_mode:
            credentials = await credentials_service.get_credentials(db, user_id, auth_mode)
            if credentials:
                return [CredentialsResponse(**credentials)]
            return []
        else:
            all_credentials = await credentials_service.get_all_credentials(db, user_id)
            return [CredentialsResponse(**cred) for cred in all_credentials]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving credentials: {str(e)}"
        )

@router.get("/active")
async def get_active_mode(
    db: AsyncSession = Depends(get_db)
):
    """Get active authentication mode - temporarily no auth for testing"""
    try:
        # Mock user ID for testing
        user_id = 1
        active_mode = await credentials_service.get_active_mode(db, user_id)
        return {
            "active_mode": active_mode,
            "message": f"Active mode: {active_mode}" if active_mode else "No active mode set"
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting active mode: {str(e)}"
        )

@router.post("/", response_model=dict)
async def save_credentials(
    credentials: CredentialsCreate,
    db: AsyncSession = Depends(get_db)
):
    """Save user credentials - temporarily no auth for testing"""
    try:
        # Mock user ID for testing
        user_id = 1
        result = await credentials_service.save_credentials(
            db=db,
            user_id=user_id,
            auth_mode=credentials.auth_mode,
            client_id=credentials.client_id,
            access_token=credentials.access_token,
            api_key=credentials.api_key,
            client_secret=credentials.client_secret,
            is_default=credentials.is_default
        )
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error saving credentials: {str(e)}"
        )

@router.post("/switch-mode", response_model=dict)
async def switch_mode(
    mode_request: ModeSwitchRequest,
    db: AsyncSession = Depends(get_db)
):
    """Switch authentication mode - temporarily no auth for testing"""
    try:
        # Mock user ID for testing
        user_id = 1
        result = await credentials_service.set_active_mode(
            db=db,
            user_id=user_id,
            auth_mode=mode_request.auth_mode
        )
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error switching mode: {str(e)}"
        )

@router.delete("/{credential_id}", response_model=dict)
async def delete_credential(
    credential_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Delete credential - temporarily no auth for testing"""
    try:
        # Mock user ID for testing
        user_id = 1
        result = await credentials_service.delete_credentials(
            db=db,
            user_id=user_id,
            credential_id=credential_id
        )
        if not result["success"]:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=result["message"]
            )
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting credential: {str(e)}"
        )
