from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from jose import jwt, JWTError
from app.api import get_db
from app.core.config import settings
from app.core.security import hash_password, verify_password, create_access_token
from app.schemas.user import UserCreate, UserOut
from app.schemas.token import Token
from app.models.user import User

router = APIRouter(prefix="/auth", tags=["auth"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")


# ---------- REGISTRO ----------

@router.post("/register", response_model=UserOut)
def register(user_in: UserCreate, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == user_in.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El email ya está registrado",
        )

    # Crear usuario nuevo
    user = User(
        nombre=user_in.nombre,
        email=user_in.email,
        password_hash=hash_password(user_in.password),
        rol=user_in.rol,
        activo=True,
    )

    db.add(user)
    db.commit()
    db.refresh(user)
    return user


# ---------- LOGIN ----------

@router.post("/login", response_model=Token)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    # Buscamos por email, porque en OAuth2PasswordRequestForm el campo se llama "username"
    user = db.query(User).filter(User.email == form_data.username).first()

    # Para depuración, distinguimos entre usuario inexistente y contraseña incorrecta
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales inválidas (usuario no encontrado)",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales inválidas (contraseña)",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Datos que irán dentro del JWT
    token_data = {"sub": str(user.id), "rol": user.rol}
    access_token = create_access_token(token_data)

    return Token(access_token=access_token)


# ---------- OBTENER USUARIO ACTUAL (para endpoints protegidos) ----------

def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token inválido o expirado",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
        user_id: str | None = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = db.query(User).get(int(user_id))
    if user is None:
        raise credentials_exception

    return user
