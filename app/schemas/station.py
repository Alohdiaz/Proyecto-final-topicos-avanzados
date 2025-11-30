from pydantic import BaseModel, ConfigDict

class StationBase(BaseModel):
    nombre: str
    tipo: str
    linea: str | None = None

class StationCreate(StationBase):
    pass

class StationOut(StationBase):
    id: int

    model_config = ConfigDict(from_attributes=True)

class StationUpdate(BaseModel):
    """
    Todos los campos opcionales, para poder hacer PATCH.
    """
    nombre: str | None = None
    tipo: str | None = None
    linea: str | None = None