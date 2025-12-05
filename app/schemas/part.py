from datetime import datetime
from typing import Set
from pydantic import BaseModel, ConfigDict, field_validator

ALLOWED_STATUS: Set[str] = {"EN_PROCESO", "OK", "SCRAP", "RETRABAJO"}

# ----- BASE COMÚN -----
class PartBase(BaseModel):
    serial: str
    tipo_pieza: str
    lote: str
    status: str = "EN_PROCESO"   # valor por defecto

    # Validador de status
    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        v_norm = v.strip().upper()
        if v_norm not in ALLOWED_STATUS:
            allowed = ", ".join(sorted(ALLOWED_STATUS))
            raise ValueError(f"Status inválido. Debe ser uno de: {allowed}")
        return v_norm


# ----- PARA CREAR PIEZA -----
class PartCreate(PartBase):
    pass


# ----- PARA RESPUESTA (INCLUYE ID Y FECHA) -----
class PartOut(PartBase):
    id: int
    fecha_creacion: datetime

    model_config = ConfigDict(from_attributes=True)  # permite partir de modelos SQLAlchemy


# ----- PARA ACTUALIZAR PIEZA (PATCH) -----
class PartUpdate(BaseModel):
    """
    Todos los campos son opcionales para permitir PATCH.
    """
    serial: str | None = None
    tipo_pieza: str | None = None
    lote: str | None = None
    status: str | None = None

    # Si el usuario manda status en PATCH, validarlo también
    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str | None) -> str | None:
        if v is None:
            return v
        v_norm = v.strip().upper()
        if v_norm not in ALLOWED_STATUS:
            allowed = ", ".join(sorted(ALLOWED_STATUS))
            raise ValueError(f"Status inválido. Debe ser uno de: {allowed}")
        return v_norm
