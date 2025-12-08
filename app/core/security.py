from datetime import datetime, timedelta
from jose import jwt
from passlib.hash import sha256_crypt  
from app.core.config import settings


def hash_password(password: str) -> str:
    """
    Hashea una contraseña usando sha256_crypt (Passlib).
    Sin límite raro de 72 bytes.
    """
    if not password or not password.strip():
        raise ValueError("La contraseña no puede estar vacía")

    return sha256_crypt.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    """
    Verifica una contraseña contra su hash.
    """
    if not plain or not hashed:
        return False

    return sha256_crypt.verify(plain, hashed)


def create_access_token(
    data: dict,
    expires_minutes: int | None = None,
) -> str:
    """
    Crea un JWT de acceso.
    """
    to_encode = data.copy()

    expire = datetime.utcnow() + timedelta(
        minutes=expires_minutes or settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    to_encode.update({"exp": expire})

    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )
    return encoded_jwt
