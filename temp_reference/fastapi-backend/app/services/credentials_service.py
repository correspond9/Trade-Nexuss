"""
Credentials Service
Handles DhanHQ credential storage, retrieval, and management
"""

import logging
from datetime import datetime
from typing import Optional, Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, and_, or_
from sqlalchemy.orm import selectinload

from app.models.credentials import DhanCredential, CredentialLog
from app.models.auth import User

logger = logging.getLogger(__name__)


class CredentialsService:
    """Service for managing DhanHQ credentials"""
    
    def __init__(self):
        self.logger = logger
    
    async def save_credentials(
        self,
        db: AsyncSession,
        user_id: int,
        auth_mode: str,
        client_id: Optional[str] = None,
        access_token: Optional[str] = None,
        api_key: Optional[str] = None,
        client_secret: Optional[str] = None,
        is_default: bool = True
    ) -> Dict[str, Any]:
        """Save or update user credentials"""
        try:
            # Validate required fields based on auth mode
            if auth_mode == "DAILY_TOKEN":
                if not client_id or not access_token:
                    raise ValueError("Client ID and Access Token are required for Daily Token mode")
            elif auth_mode == "STATIC_IP":
                if not api_key or not client_secret:
                    raise ValueError("API Key and Client Secret are required for Static IP mode")
            else:
                raise ValueError("Invalid auth mode. Must be DAILY_TOKEN or STATIC_IP")
            
            # Check if credentials already exist for this user and mode
            existing = await db.execute(
                select(DhanCredential).where(
                    and_(
                        DhanCredential.user_id == user_id,
                        DhanCredential.auth_mode == auth_mode
                    )
                )
            )
            existing_credential = existing.scalar_one_or_none()
            
            if existing_credential:
                # Update existing credentials
                await db.execute(
                    update(DhanCredential)
                    .where(DhanCredential.id == existing_credential.id)
                    .values(
                        client_id=client_id,
                        access_token=access_token,
                        api_key=api_key,
                        client_secret=client_secret,
                        is_default=is_default,
                        updated_at=datetime.utcnow()
                    )
                )
                credential_id = existing_credential.id
                action = "UPDATED"
            else:
                # Create new credentials
                new_credential = DhanCredential(
                    user_id=user_id,
                    auth_mode=auth_mode,
                    client_id=client_id,
                    access_token=access_token,
                    api_key=api_key,
                    client_secret=client_secret,
                    is_default=is_default
                )
                db.add(new_credential)
                await db.flush()
                credential_id = new_credential.id
                action = "CREATED"
            
            # If this is default, unset other defaults for same mode
            if is_default:
                await db.execute(
                    update(DhanCredential)
                    .where(
                        and_(
                            DhanCredential.user_id == user_id,
                            DhanCredential.auth_mode == auth_mode,
                            DhanCredential.id != credential_id
                        )
                    )
                    .values(is_default=False)
                )
            
            await db.commit()
            
            # Log the action
            await self._log_credential_action(
                db, credential_id, user_id, action, "SUCCESS",
                f"Credentials {action.lower()} for {auth_mode} mode"
            )
            
            return {
                "success": True,
                "message": f"Credentials {action.lower()} successfully",
                "credential_id": credential_id,
                "auth_mode": auth_mode
            }
            
        except Exception as e:
            await db.rollback()
            self.logger.error(f"Error saving credentials: {e}")
            raise
    
    async def get_credentials(
        self,
        db: AsyncSession,
        user_id: int,
        auth_mode: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Get user credentials"""
        try:
            query = select(DhanCredential).where(DhanCredential.user_id == user_id)
            
            if auth_mode:
                query = query.where(DhanCredential.auth_mode == auth_mode)
            
            # Get default credentials for the mode, or first available
            query = query.where(DhanCredential.is_active == True)
            query = query.order_by(DhanCredential.is_default.desc(), DhanCredential.created_at.desc())
            
            result = await db.execute(query)
            credential = result.scalar_one_or_none()
            
            if not credential:
                return None
            
            # Update last used timestamp
            await db.execute(
                update(DhanCredential)
                .where(DhanCredential.id == credential.id)
                .values(last_used_at=datetime.utcnow())
            )
            await db.commit()
            
            # Return credential data (mask sensitive fields for logging)
            return {
                "id": credential.id,
                "auth_mode": credential.auth_mode,
                "client_id": credential.client_id,
                "access_token": credential.access_token,  # Return full token for frontend use
                "api_key": credential.api_key,
                "client_secret": credential.client_secret,
                "is_default": credential.is_default,
                "created_at": credential.created_at.isoformat() if credential.created_at else None,
                "last_used_at": credential.last_used_at.isoformat() if credential.last_used_at else None
            }
            
        except Exception as e:
            self.logger.error(f"Error retrieving credentials: {e}")
            return None
    
    async def get_all_credentials(
        self,
        db: AsyncSession,
        user_id: int
    ) -> List[Dict[str, Any]]:
        """Get all user credentials"""
        try:
            result = await db.execute(
                select(DhanCredential)
                .where(DhanCredential.user_id == user_id)
                .where(DhanCredential.is_active == True)
                .order_by(DhanCredential.auth_mode, DhanCredential.is_default.desc())
            )
            credentials = result.scalars().all()
            
            return [
                {
                    "id": cred.id,
                    "auth_mode": cred.auth_mode,
                    "client_id": cred.client_id,
                    "access_token": cred.access_token,
                    "api_key": cred.api_key,
                    "client_secret": cred.client_secret,
                    "is_default": cred.is_default,
                    "created_at": cred.created_at.isoformat() if cred.created_at else None,
                    "last_used_at": cred.last_used_at.isoformat() if cred.last_used_at else None
                }
                for cred in credentials
            ]
            
        except Exception as e:
            self.logger.error(f"Error retrieving all credentials: {e}")
            return []
    
    async def delete_credentials(
        self,
        db: AsyncSession,
        user_id: int,
        credential_id: int
    ) -> Dict[str, Any]:
        """Delete user credentials"""
        try:
            # Check if credential exists and belongs to user
            result = await db.execute(
                select(DhanCredential).where(
                    and_(
                        DhanCredential.id == credential_id,
                        DhanCredential.user_id == user_id
                    )
                )
            )
            credential = result.scalar_one_or_none()
            
            if not credential:
                return {
                    "success": False,
                    "message": "Credential not found"
                }
            
            # Soft delete (mark as inactive)
            await db.execute(
                update(DhanCredential)
                .where(DhanCredential.id == credential_id)
                .values(is_active=False)
            )
            await db.commit()
            
            # Log the action
            await self._log_credential_action(
                db, credential_id, user_id, "DELETED", "SUCCESS",
                f"Credentials deleted for {credential.auth_mode} mode"
            )
            
            return {
                "success": True,
                "message": "Credentials deleted successfully"
            }
            
        except Exception as e:
            await db.rollback()
            self.logger.error(f"Error deleting credentials: {e}")
            return {
                "success": False,
                "message": f"Error deleting credentials: {str(e)}"
            }
    
    async def set_active_mode(
        self,
        db: AsyncSession,
        user_id: int,
        auth_mode: str
    ) -> Dict[str, Any]:
        """Set the active authentication mode for user"""
        try:
            # Check if credentials exist for this mode
            result = await db.execute(
                select(DhanCredential).where(
                    and_(
                        DhanCredential.user_id == user_id,
                        DhanCredential.auth_mode == auth_mode,
                        DhanCredential.is_active == True
                    )
                )
            )
            credential = result.scalar_one_or_none()
            
            if not credential:
                return {
                    "success": False,
                    "message": f"No credentials found for {auth_mode} mode"
                }
            
            # Set as default
            await db.execute(
                update(DhanCredential)
                .where(DhanCredential.id == credential.id)
                .values(is_default=True)
            )
            await db.commit()
            
            # Log the action
            await self._log_credential_action(
                db, credential.id, user_id, "MODE_SWITCH", "SUCCESS",
                f"Switched to {auth_mode} mode"
            )
            
            return {
                "success": True,
                "message": f"Active mode set to {auth_mode}",
                "auth_mode": auth_mode
            }
            
        except Exception as e:
            await db.rollback()
            self.logger.error(f"Error setting active mode: {e}")
            return {
                "success": False,
                "message": f"Error setting active mode: {str(e)}"
            }
    
    async def get_active_mode(
        self,
        db: AsyncSession,
        user_id: int
    ) -> Optional[str]:
        """Get the active authentication mode for user"""
        try:
            result = await db.execute(
                select(DhanCredential.auth_mode)
                .where(
                    and_(
                        DhanCredential.user_id == user_id,
                        DhanCredential.is_active == True,
                        DhanCredential.is_default == True
                    )
                )
                .order_by(DhanCredential.created_at.desc())
                .limit(1)
            )
            auth_mode = result.scalar_one_or_none()
            return auth_mode
            
        except Exception as e:
            self.logger.error(f"Error getting active mode: {e}")
            return None
    
    async def _log_credential_action(
        self,
        db: AsyncSession,
        credential_id: int,
        user_id: int,
        action: str,
        status: str,
        message: str,
        error_details: Optional[str] = None
    ):
        """Log credential actions"""
        try:
            log_entry = CredentialLog(
                credential_id=credential_id,
                user_id=user_id,
                action=action,
                status=status,
                message=message,
                error_details=error_details
            )
            db.add(log_entry)
            await db.commit()
            
        except Exception as e:
            self.logger.error(f"Error logging credential action: {e}")


# Global service instance
credentials_service = CredentialsService()
