from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime  
from app.schemas.ai import RiskInput, RiskOutput
from app.api import get_db
from app.models.trace_event import TraceEvent
from app.models.part import Part
from app.models.station import Station
from app.core.roles import require_supervisor_or_admin
from app.schemas.trace_event import TraceEventCreate, TraceEventOut  
from app.core.roles import require_user  # Asegúrate de importar correctamente


router = APIRouter(prefix="/ai", tags=["ai"])


# ---------------------- Risk Score (based on rules) ---------------------- #
@router.post("/risk-score", response_model=RiskOutput)
def risk_score(data: RiskInput):
    # Validación de datos
    if data.tiempo_total_segundos < 0:
        raise HTTPException(status_code=400, detail="El tiempo total no puede ser negativo.")
    if data.num_retrabajos < 0:
        raise HTTPException(status_code=400, detail="El número de retrabajos no puede ser negativo.")

    score = 0.0
    explicaciones = []

    # Evaluación de tiempo total
    if data.tiempo_total_segundos > 900:
        score += 0.4
        explicaciones.append("Tiempo total muy superior al promedio esperado.")
    elif data.tiempo_total_segundos > 600:
        score += 0.2
        explicaciones.append("Tiempo total algo superior al promedio.")

    # Evaluación de retrabajos
    if data.num_retrabajos >= 2:
        score += 0.4
        explicaciones.append("Tiene múltiples retrabajos.")
    elif data.num_retrabajos == 1:
        score += 0.2
        explicaciones.append("Tiene un retrabajo registrado.")

    # Evaluación de estación
    if data.estacion_actual.upper().startswith("INSPECCION"):
        score += 0.1
        explicaciones.append("Se encuentra en inspección final.")

    # Limitar entre 0 y 1
    score = min(score, 1.0)

    # Determinación de nivel de riesgo
    if score >= 0.7:
        nivel = "ALTO"
    elif score >= 0.4:
        nivel = "MEDIO"
    else:
        nivel = "BAJO"

    print(f"Riesgo Falla: {score}, Nivel: {nivel}, Explicación: {', '.join(explicaciones)}")
    return RiskOutput(
        riesgo_falla=score,
        nivel=nivel,
        explicacion=" ".join(explicaciones) or "Riesgo bajo según reglas actuales.",
    )


# ---------------------- Risk Score for Part ---------------------- #
@router.post("/risk-score/{part_id}")
def risk_score_part(
    part_id: int, 
    db: Session = Depends(get_db), 
    current_user=Depends(require_supervisor_or_admin)
):
    # Verificar si la pieza existe
    if not db.query(Part).filter(Part.id == part_id).first():
        raise HTTPException(status_code=404, detail="La pieza no existe.")

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

    scrap_count = sum(ev.resultado == "SCRAP" for ev in events)
    retrabajo_count = sum(ev.resultado == "RETRABAJO" for ev in events)

    riesgo = 0
    razones = []

    # Evaluación de tiempo total
    if float(total_time) > 900:
        riesgo += 0.4
        razones.append("Tiempo total elevado.")
    elif float(total_time) > 600:
        riesgo += 0.2
        razones.append("Tiempo total encima del promedio.")

    # Evaluación de SCRAP
    if scrap_count > 0:
        riesgo += 0.4
        razones.append("Historial de SCRAP.")

    # Evaluación de retrabajos
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

# ---------------------- Anomalies ---------------------- #
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


@router.post("/", response_model=TraceEventOut)
def create_trace_event(
    event_in: TraceEventCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_user),
):
    # Validar que existan la pieza y la estación
    part = db.query(Part).get(event_in.part_id)
    if not part:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pieza no encontrada.",
        )

    station = db.query(Station).get(event_in.station_id)
    if not station:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Estación no encontrada.",
        )

    # Verificar que el resultado sea uno de los válidos
    if event_in.resultado in {"OK", "SCRAP", "RETRABAJO"}:
        part.status = event_in.resultado
        db.add(part)

        # Si el evento es SCRAP o RETRABAJO, establecer la salida
        if event_in.resultado in {"SCRAP", "RETRABAJO"}:
            event_in.timestamp_salida = datetime.utcnow()  # Establecer el tiempo de salida si corresponde

    event = TraceEvent(**event_in.model_dump())  # Crear el evento de traza
    db.add(event)

    db.commit()
    db.refresh(event)
    return event
