# app/schemas/trace_event.py
from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime
from typing import Optional


# ========== Schemas para Risk Score ==========
class RiskScoreDetails(BaseModel):
    """Detalles del cálculo del risk score"""
    tiempo_total_segundos: float
    tiempo_total_minutos: float
    eventos_totales: int
    scrap_count: int
    retrabajo_count: int

    model_config = ConfigDict(from_attributes=True)


class RiskScoreData(BaseModel):
    """Datos del risk score calculado"""
    riesgo: float = Field(..., ge=0, le=1, description="Valor del riesgo (0-1)")
    nivel: str = Field(..., description="Nivel de riesgo: BAJO, MEDIO, ALTO")
    razones: list[str] = Field(default=[], description="Lista de razones del riesgo")
    detalles: RiskScoreDetails

    model_config = ConfigDict(from_attributes=True)


# ========== Schemas de TraceEvent (Tu código original) ==========
class TraceEventBase(BaseModel):
    part_id: int
    station_id: int
    operador_id: int | None = None
    resultado: str
    observaciones: str | None = None
    timestamp_salida: datetime | None = None


class TraceEventCreate(TraceEventBase):
    """Schema para crear un nuevo evento de traza"""
    pass


class TraceEventOut(TraceEventBase):
    """Schema para la respuesta de un evento de traza"""
    id: int
    timestamp_entrada: datetime
    risk_score: Optional[RiskScoreData] = None  # ← NUEVO: Campo agregado para el risk score

    model_config = ConfigDict(from_attributes=True)