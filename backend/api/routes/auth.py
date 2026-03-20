"""
Authentication router.

Handles user registration, login (JWT issuance), token refresh, and
logout for the MachineSearch admin panel.  Uses OAuth2 password flow
with short-lived access tokens and longer-lived refresh tokens.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm

router = APIRouter()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token")

# TODO: implement token creation with python-jose
# TODO: implement password hashing with passlib[bcrypt]
# TODO: load SECRET_KEY from environment / settings


@router.post("/token")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """
    Issue a JWT access token for valid credentials.

    TODO: verify user against DB hashed password.
    TODO: return {"access_token": ..., "token_type": "bearer"}.
    TODO: also set a refresh token in an HttpOnly cookie.
    """
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication not yet implemented",
    )


@router.post("/refresh")
async def refresh_token():
    """
    Issue a new access token using a valid refresh token cookie.

    TODO: validate refresh token from HttpOnly cookie.
    TODO: return new access token in response body.
    """
    raise HTTPException(status_code=501, detail="Not implemented")


@router.post("/logout")
async def logout():
    """
    Invalidate the current session.

    TODO: blacklist the refresh token in Redis or DB.
    TODO: clear the refresh token cookie in the response.
    """
    return {"message": "Logged out"}


@router.get("/me")
async def get_current_user(token: str = Depends(oauth2_scheme)):
    """
    Return the profile of the currently authenticated user.

    TODO: decode JWT, fetch user record from DB.
    """
    raise HTTPException(status_code=501, detail="Not implemented")
