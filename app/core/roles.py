from fastapi import Depends, HTTPException, status
from app.api.auth import get_current_user
from app.models.user import User

Permited_roles = {"OPERADOR","SUPERVISOR", "ADMIN"}

def require_user(current_user: User = Depends(get_current_user)) -> User:
    """
    Solo exige que el usuario esté autenticado.
    """
    return current_user


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """
    Solo permite usuarios con rol ADMIN.
    """
    if current_user.rol != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permiso, se requiere rol ADMIN.",
        )
    return current_user


def require_supervisor_or_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Permite SUPERVISOR o ADMIN.
    """
    if current_user.rol not in ("SUPERVISOR", "ADMIN"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permiso, se requiere rol SUPERVISOR o ADMIN.",
        )
    return current_user


def require_operator_or_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Permite OPERADOR o ADMIN.
    """
    if current_user.rol not in ("OPERADOR", "ADMIN"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permiso, se requiere rol OPERADOR o ADMIN.",
        )
    return current_user
