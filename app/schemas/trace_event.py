from pydantic import BaseModel, ConfigDict
from datetime import datetime

class TraceEventBase(BaseModel):
    part_id: int
    station_id: int
    operador_id: int | None = None
    resultado: str
    observaciones: str | None = None
    timestamp_salida: datetime | None = None

class TraceEventCreate(TraceEventBase):
    pass

class TraceEventOut(TraceEventBase):
    id: int
    timestamp_entrada: datetime

    model_config = ConfigDict(from_attributes=True)
