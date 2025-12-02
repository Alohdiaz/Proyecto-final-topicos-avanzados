from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.schemas.ai import RiskInput, RiskOutput
from app.api import get_db
from app.models.trace_event import TraceEvent
from app.models.part import Part
from app.core.roles import require_supervisor_or_admin
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

@router.post("/risk-score/{part_id}")
def risk_score_part(
    part_id: str, 
    db: Session = Depends(get_db), 
    current_user=Depends(require_supervisor_or_admin)
    ):
        events = (
        db.query(TraceEvent)
        .filter(TraceEvent.part_id == part_id)
        .all()
        )
        if not events:
            return {
                "part_id": part_id,
                "riesgo": 0.0,
                "razon": "No hay eventos registrados para esta pieza."
            }
        
        total_time = sum(
            (ev.timestamp_salida - ev.timestamp_entrada).total_seconds()
            for ev in events
        )

        scrap_count = sum(ev.resultado == Part.SCRAP for ev in events)

        retrabajo_count = sum(ev.resultado == Part.RETRABAJO for ev in events)

        riesgo = 0
        razones = []

        if float(total_time) > 900:
            riesgo += 0.4
            razones.append("Tiempo total elevado.")
        elif float(total_time) > 600:
            riesgo += 0.2
            razones.append("Tiempo total encima del promedio.")

        if scrap_count > 0:
            riesgo += 0.4
            razones.append("Historial de SCRAP.")

        if retrabajo_count >= 2:
            riesgo += 0.2
            razones.append("Múltiples retrabajos.")
        elif retrabajo_count == 1:
            riesgo += 0.1
            razones.append("Un retrabajo registrado.")

        return {
            "part_id": part_id,
            "tiempo_total": total_time,
            "scrap_count": scrap_count,
            "retrabaos": retrabajo_count,
            "riesgo": min(riesgo, 1.0),
            "razones": razones
        }

@router.get("/anomalies")
def anomalies(
    db: Session = Depends(get_db),
    current_user=Depends(require_supervisor_or_admin)
):
    avg_time = db.query(
        func.avg(
            func.extract(
                "epoch",
                TraceEvent.timestamp_salida - TraceEvent.timestamp_entrada
            )
        )
    ).scalar()

    if not avg_time:
        return []

    threshold = float(avg_time) * 1.5  # 50% arriba del promedio

    rows = (
        db.query(
            TraceEvent.part_id,
            func.sum(
                func.extract(
                    "epoch",
                    TraceEvent.timestamp_salida - TraceEvent.timestamp_entrada
                )
            ).label("total_time")
        )
        .group_by(TraceEvent.part_id)
        .having(func.sum(
            func.extract(
                "epoch",
                TraceEvent.timestamp_salida - TraceEvent.timestamp_entrada
            )
        ) > threshold)
        .all()
    )

    return [
        {
            "part_id": part_id,
            "tiempo_total_seg": total_time,
            "porcentaje_sobre_promedio": round((total_time / avg_time) * 100, 2),
        }
        for part_id, total_time in rows
    ]