from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.user import User
from app.schemas.user import UserOut, UserCreate, UserUpdate
from app.core.roles import require_admin
from app.api.auth import get_current_user

router = APIRouter(prefix="/users", tags=["users"])

#------------------ FUNCION PARA REQUERIR ADMIN ------------------ #
"""
def require_admin(user: User = Depends(get_current_user)):
    if user.rol != "ADMIN":
        raise HTTPException(
            status_code=403
        )
    return user
"""

# ------------------ CREAR USUARIO (ADMIN) ------------------ #

@router.post("/", response_model=UserOut)
def create_user(
    user_in: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),  
):
    """
    Solo ADMIN puede crear usuarios.
    """
    existing_user = db.query(User).filter(User.email == user_in.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El usuario con este email ya está registrado."
        )
    
    user = User(**user_in.dict())
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


# ------------------ LISTAR USUARIOS (ADMIN) ------------------ #
@router.get("/", response_model=list[UserOut])
def list_users(
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """
    Solo ADMIN puede listar los usuarios.
    """
    return db.query(User).order_by(User.id).all()


# -------------------- OBTENER USUARIO POR ID (ADMIN) -------------------- #
@router.get("/{user_id}", response_model=UserOut)
def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """
    Solo ADMIN puede ver un usuario por su ID.
    """
    user = db.query(User).get(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado"
        )
    return user


# -------------------- ACTUALIZAR USUARIO (ADMIN) -------------------- #
@router.patch("/{user_id}", response_model=UserOut)
def update_user(
    user_id: int,
    user_in: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """
    Solo ADMIN puede actualizar usuarios.
    """
    user = db.query(User).get(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado"
        )

    data = user_in.model_dump(exclude_unset=True)

    # Si quieren cambiar el rol, validarlo
    if "rol" in data:
        if data["rol"] not in ["OPERADOR", "SUPERVISOR", "ADMIN"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Rol inválido. Debe ser uno de: OPERADOR, SUPERVISOR, ADMIN"
            )

    for field, value in data.items():
        setattr(user, field, value)

    db.add(user)
    db.commit()
    db.refresh(user)
    return user


# -------------------- ELIMINAR USUARIO (ADMIN) -------------------- #

@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """
    Solo ADMIN puede eliminar usuarios.
    """
    user = db.query(User).get(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado"
        )

    db.delete(user)
    db.commit()
    return {"message": "Usuario eliminado correctamente"}
