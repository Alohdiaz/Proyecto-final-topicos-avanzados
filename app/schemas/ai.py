from pydantic import BaseModel
from typing import List


class RiskInput(BaseModel):
    part_id: int
    num_retrabajos: int
    tiempo_total_segundos: int
    estacion_actual: str
    tipo_pieza: str


class RiskOutput(BaseModel):
    riesgo_falla: float
    nivel: str
    explicacion: str


class PartRiskScore(BaseModel):
    part_id: int
    tiempo_total: float
    scrap_count: int
    retrabajos: int
    riesgo: float
    razones: List[str]
