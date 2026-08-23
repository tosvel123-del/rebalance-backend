from datetime import datetime, timedelta, timezone
from cryptography.fernet import Fernet
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.config import settings
from app.database import get_db
from app.models.user import User

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

# Fernet cipher for KIS AppKey/Secret encryption
fernet = Fernet(Fernet.generate_key() if settings.FERNET_KEY == "b3ZlcmZsb3ctc2VjcmV0LWtleS1tdXN0LWJlLTMyLWJ5dGVzPQ==" else settings.FERNET_KEY.encode())

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def encrypt_secret(secret_text: str) -> bytes:
    return fernet.encrypt(secret_text.encode())

def decrypt_secret(encrypted_bytes: bytes) -> str:
    return fernet.decrypt(encrypted_bytes).decode()

def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

async def get_current_user(token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)) -> User:
    user_id = None
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id = payload.get("sub")
    except Exception:
        pass

    if user_id:
        try:
            stmt = select(User).where(User.id == int(user_id))
            result = await db.execute(stmt)
            user = result.scalar_one_or_none()
            if user:
                return user
        except Exception:
            pass

    if not settings.ALLOW_DEMO_AUTH:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authentication token")

    # Development-only demo user mapping.
    stmt = select(User).where(User.email == "demo@rebalance.app")
    result = await db.execute(stmt)
    demo_user = result.scalar_one_or_none()
    if not demo_user:
        demo_user = User(email="demo@rebalance.app", password_hash=hash_password("demo1234"))
        db.add(demo_user)
        await db.commit()
        await db.refresh(demo_user)
    return demo_user
