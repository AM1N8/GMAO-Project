"""
Security module for verifying JWT tokens and authenticating users.
Integrates with Makerkit (Supabase) auth.

Architecture:
- Supabase app_metadata.role is the SINGLE SOURCE OF TRUTH for user roles
- Auth users are separate from domain models (Technician)
- Role guards enforce RBAC at the API level
"""

import os
import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Technician, UserRole

# Logger
logger = logging.getLogger(__name__)

# Security scheme
security = HTTPBearer()
optional_security = HTTPBearer(auto_error=False)

# Configuration
JWT_SECRET = os.getenv("JWT_SECRET", os.getenv("SUPABASE_JWT_SECRET"))
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")

# Default role for users without explicit role assignment
DEFAULT_ROLE = UserRole.VIEWER


@dataclass
class AuthUser:
    """
    Authenticated user from JWT claims.
    Separate from domain models like Technician.
    Role is sourced from Supabase app_metadata (single source of truth).
    """
    id: str  # Supabase user ID (sub claim)
    email: str
    role: UserRole
    raw_claims: Dict[str, Any]
    
    @property
    def is_admin(self) -> bool:
        return self.role == UserRole.ADMIN
    
    @property
    def is_supervisor(self) -> bool:
        return self.role == UserRole.SUPERVISOR
    
    @property
    def is_technician(self) -> bool:
        return self.role == UserRole.TECHNICIAN
    
    @property
    def is_viewer(self) -> bool:
        return self.role == UserRole.VIEWER
    
    def has_role(self, roles: List[UserRole]) -> bool:
        """Check if user has any of the specified roles."""
        return self.role in roles


async def get_token_payload(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Dict[str, Any]:
    """
    Verify the JWT token and return the payload.
    """
    token = credentials.credentials
    
    if not JWT_SECRET:
        logger.error("JWT_SECRET not set. Authentication cannot proceed.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Server authentication configuration error"
        )

    try:
        payload = jwt.decode(
            token, 
            JWT_SECRET, 
            algorithms=[JWT_ALGORITHM], 
            options={"verify_aud": False}
        )
        return payload
    except JWTError as e:
        logger.error(f"JWT Verification failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


def _extract_role_from_claims(payload: Dict[str, Any]) -> UserRole:
    """
    Extract user role from JWT claims.
    Supabase stores custom claims in app_metadata.
    """
    # Try app_metadata.role first (Supabase standard)
    app_metadata = payload.get("app_metadata", {})
    role_value = app_metadata.get("role")
    
    # Fallback: check user_metadata (some setups use this)
    if not role_value:
        user_metadata = payload.get("user_metadata", {})
        role_value = user_metadata.get("role")
    
    # Fallback: check top-level role claim
    if not role_value:
        role_value = payload.get("role")
    
    # Validate and return role
    if role_value:
        try:
            return UserRole(role_value)
        except ValueError:
            logger.warning(f"Invalid role value in JWT: {role_value}. Using default.")
    
    return DEFAULT_ROLE


async def get_auth_user(
    payload: Dict[str, Any] = Depends(get_token_payload)
) -> AuthUser:
    """
    Get the authenticated user from JWT claims.
    This is the primary authentication dependency.
    Role is extracted from Supabase app_metadata (single source of truth).
    """
    user_id = payload.get("sub")
    email = payload.get("email")
    
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing subject claim"
        )
    
    if not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing email claim"
        )
    
    role = _extract_role_from_claims(payload)
    
    return AuthUser(
        id=user_id,
        email=email,
        role=role,
        raw_claims=payload
    )


async def get_auth_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(optional_security)
) -> Optional[AuthUser]:
    """
    Optional authentication - returns None if no valid token.
    Useful for endpoints that have public/private modes.
    """
    if not credentials:
        return None
    
    try:
        payload = await get_token_payload(credentials)
        return await get_auth_user(payload)
    except HTTPException:
        return None


# ==================== ROLE GUARDS ====================

def require_role(allowed_roles: List[UserRole]):
    """
    Dependency factory for role-based access control.
    
    Usage:
        @router.post("/", dependencies=[Depends(require_role([UserRole.ADMIN, UserRole.SUPERVISOR]))])
        async def create_item(...):
            ...
    
    Or with access to the user:
        @router.post("/")
        async def create_item(auth_user: AuthUser = Depends(require_role([UserRole.ADMIN]))):
            ...
    """
    async def role_checker(
        auth_user: AuthUser = Depends(get_auth_user)
    ) -> AuthUser:
        if auth_user.role not in allowed_roles:
            logger.warning(
                f"Access denied for user {auth_user.email} with role {auth_user.role}. "
                f"Required roles: {[r.value for r in allowed_roles]}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required role: {', '.join(r.value for r in allowed_roles)}"
            )
        return auth_user
    
    return role_checker


def require_admin():
    """Shorthand for requiring admin role."""
    return require_role([UserRole.ADMIN])


def require_supervisor_or_admin():
    """Shorthand for requiring supervisor or admin role."""
    return require_role([UserRole.ADMIN, UserRole.SUPERVISOR])


def require_technician_or_above():
    """Shorthand for requiring technician, supervisor, or admin role."""
    return require_role([UserRole.ADMIN, UserRole.SUPERVISOR, UserRole.TECHNICIAN])


# ==================== LEGACY COMPATIBILITY ====================
# These functions maintain backward compatibility with existing code
# that expects a Technician object from authentication.

async def get_current_user(
    auth_user: AuthUser = Depends(get_auth_user),
    db: Session = Depends(get_db)
) -> Technician:
    """
    LEGACY: Get the Technician domain entity linked to the authenticated user.
    
    Note: This couples auth identity to Technician domain model.
    Consider using get_auth_user directly for new code.
    """
    technician = db.query(Technician).filter(Technician.email == auth_user.email).first()
    
    if not technician:
        logger.warning(f"User {auth_user.email} not found in Technicians table.")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User not registered as a technician in this system"
        )
    
    return technician


async def get_current_user_optional(
    auth_user: Optional[AuthUser] = Depends(get_auth_user_optional),
    db: Session = Depends(get_db)
) -> Optional[Technician]:
    """
    LEGACY: Optional technician lookup.
    """
    if not auth_user:
        return None
    
    try:
        return await get_current_user(auth_user, db)
    except HTTPException:
        return None
