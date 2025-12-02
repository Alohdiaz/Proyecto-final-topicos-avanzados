from pydantic import BaseModel

class RiskInput(BaseModel):
    part_id: str
    num_retrabajos: int
    tiempo_total_segundos: int
    estacion_actual: str
    tipo_pieza: str

class RiskOutput(BaseModel):
    riesgo_falla: float
    nivel: str
    explicacion: str
