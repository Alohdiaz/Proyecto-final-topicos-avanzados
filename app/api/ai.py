from fastapi import APIRouter
from app.schemas.ai import RiskInput, RiskOutput

router = APIRouter(prefix="/ai", tags=["ai"])

@router.post("/risk-score", response_model=RiskOutput)
def risk_score(data: RiskInput):
    score = 0.0
    explicaciones = []

    if data.tiempo_total_segundos > 900:
        score += 0.4
        explicaciones.append("Tiempo total muy superior al promedio esperado.")
    elif data.tiempo_total_segundos > 600:
        score += 0.2
        explicaciones.append("Tiempo total algo superior al promedio.")

    if data.num_retrabajos >= 2:
        score += 0.4
        explicaciones.append("Tiene múltiples retrabajos.")
    elif data.num_retrabajos == 1:
        score += 0.2
        explicaciones.append("Tiene un retrabajo registrado.")

    if data.estacion_actual.upper().startswith("INSPECCION"):
        score += 0.1
        explicaciones.append("Se encuentra en inspección final.")

    # Limitar entre 0 y 1
    score = min(score, 1.0)

    if score >= 0.7:
        nivel = "ALTO"
    elif score >= 0.4:
        nivel = "MEDIO"
    else:
        nivel = "BAJO"

    return RiskOutput(
        riesgo_falla=score,
        nivel=nivel,
        explicacion=" ".join(explicaciones) or "Riesgo bajo según reglas actuales.",
    )
