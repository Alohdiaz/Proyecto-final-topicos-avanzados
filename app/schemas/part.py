from datetime import datetime
from pydantic import BaseModel, ConfigDict


# ----- BASE COMÚN -----
class PartBase(BaseModel):
    serial: str
    tipo_pieza: str
    lote: str
    status: str  # EN_PROCESO, OK, SCRAP, RETRABAJO


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
    Todos los campos opcionales, para poder hacer PATCH.
    """
    serial: str | None = None
    tipo_pieza: str | None = None
    lote: str | None = None
    status: str | None = None

    
