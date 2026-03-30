import os
import jwt
import base64
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv

load_dotenv()

# Configuration for JWT verification.
RAW_SECRET = os.getenv("SECRET_KEY", "your-default-secret-key-for-dev")
ALGORITHM = "HS256"

print("enter")

def decode_secret(secret: str):
    """Decodes a base64Url encoded secret string into bytes."""
    try:
        # Add padding if missing
        rem = len(secret) % 4
        if rem > 0:
            secret += "=" * (4 - rem)
        return base64.urlsafe_b64decode(secret)
    except Exception:
        # Fallback to raw string if decoding fails
        return secret

SECRET_KEY = decode_secret(RAW_SECRET)

# This dependency will look for the "Authorization: Bearer <token>" header
security = HTTPBearer()

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """
    Decodes the JWT and validates the user.
    If validation fails, it raises an HTTP 401 exception.
    """
    token = credentials.credentials
    try:
        # Decode the token using the secret key
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        
        # In a real system, you might verify the "sub" or roles here.
        # For now, if it decodes, it's considered authorized.
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication token: missing subject (sub)",
            )
        return {"user_id": user_id, "token": token}

    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token has expired",
        )
    except jwt.InvalidSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token signature. Check your JWT_SECRET_KEY.",
        )
    except jwt.DecodeError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token is malformed or could not be decoded.",
        )
    except jwt.PyJWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"JWT Validation Error: {str(e)}",
        )
