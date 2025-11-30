from datetime import datetime
from typing import Set
from pydantic import BaseModel, EmailStr, ConfigDict, field_validator

# Conjunto de roles válidos en TODO el sistema
ALLOWED_ROLES: Set[str] = {"OPERADOR", "SUPERVISOR", "ADMIN"}


class UserBase(BaseModel):
    nombre: str
    email: EmailStr
    rol: str = "OPERADOR"
    activo: bool = True

    @field_validator("rol")
    @classmethod
    def validate_rol(cls, v: str) -> str:
        """
        Normaliza y valida el rol.
        - lo pasa a mayúsculas
        - Rechaza cualquier valor que no esté en ALLOWED_ROLES
        """
        if not v:
            raise ValueError("El rol no puede estar vacío")
        
        rol_normalizado = v.strip().upper()

        if rol_normalizado not in ALLOWED_ROLES:
            # Esto es lo que verá el cliente si manda un rol inventado
            roles_str = " - ".join(sorted(ALLOWED_ROLES))
            raise ValueError(f"Rol inválido. Debe ser uno de: {roles_str}")
        
        return rol_normalizado


class UserCreate(UserBase):
    password: str

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("La contraseña no puede estar vacía")
        
        if len(v) < 6:
            raise ValueError("La contraseña debe tener al menos 6 caracteres")

        # El límite superior lo maneja security.py (bcrypt)
        return v


class UserOut(UserBase):
    id: int
    fecha_registro: datetime

    # Para convertir automáticamente desde objetos SQLAlchemy
    model_config = ConfigDict(from_attributes=True)


# Clase adicional para actualizar usuarios (necesaria para PATCH)
class UserUpdate(UserBase):
    password: str | None = None
    rol: str | None = None
