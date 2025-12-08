'''
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
from app.core.roles import require_user  


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
'''

# app/api/ai.py

from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel

from app.db.session import get_db  # OJO: desde db.session, no desde app.api
from app.schemas.ai import RiskInput, RiskOutput
from app.models.trace_event import TraceEvent
from app.models.part import Part
from app.core.roles import require_supervisor_or_admin

router = APIRouter(prefix="/ai", tags=["ai"])


# ======================== MODELO DE RESPUESTA PARA /risk-score/{part_id} ========================
class PartRiskScore(BaseModel):
    part_id: int
    tiempo_total: float
    scrap_count: int
    retrabajos: int
    riesgo: float
    razones: List[str]


# ======================== RISK SCORE BASADO EN REGLAS (INPUT MANUAL) ========================
@router.post("/risk-score", response_model=RiskOutput)
def risk_score(data: RiskInput):
    """
    Calcula el riesgo de falla a partir de datos agregados enviados en el body.
    No depende de la base de datos; solo aplica reglas sobre los valores recibidos.
    """
    # Validación de datos
    if data.tiempo_total_segundos < 0:
        raise HTTPException(status_code=400, detail="El tiempo total no puede ser negativo.")
    if data.num_retrabajos < 0:
        raise HTTPException(status_code=400, detail="El número de retrabajos no puede ser negativo.")

    score = 0.0
    explicaciones: List[str] = []

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

    return RiskOutput(
        riesgo_falla=score,
        nivel=nivel,
        explicacion=" ".join(explicaciones) or "Riesgo bajo según reglas actuales.",
    )


# ======================== RISK SCORE PARA UNA PIEZA (USANDO TRACE EVENTS) ========================
@router.post("/risk-score/{part_id}", response_model=PartRiskScore)
def risk_score_part(
    part_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_supervisor_or_admin),
):
    """
    Calcula el riesgo de una pieza en base a todos sus TraceEvents.
    Usa los tiempos de proceso, SCRAPs y retrabajos registrados en la BD.
    """
    # Verificar si la pieza existe
    part = db.query(Part).filter(Part.id == part_id).first()
    if not part:
        raise HTTPException(status_code=404, detail="La pieza no existe.")

    events = (
        db.query(TraceEvent)
        .filter(TraceEvent.part_id == part_id)
        .all()
    )

    if not events:
        return PartRiskScore(
            part_id=part_id,
            tiempo_total=0.0,
            scrap_count=0,
            retrabajos=0,
            riesgo=0.0,
            razones=["No hay eventos registrados para esta pieza."],
        )

    # Calcular tiempo total SOLO cuando ambos timestamps existen
    total_time = 0.0
    for ev in events:
        if ev.timestamp_entrada and ev.timestamp_salida:
            delta = (ev.timestamp_salida - ev.timestamp_entrada).total_seconds()
            total_time += delta

    scrap_count = sum(1 for ev in events if ev.resultado == "SCRAP")
    retrabajo_count = sum(1 for ev in events if ev.resultado == "RETRABAJO")

    riesgo = 0.0
    razones: List[str] = []

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

    # Si no hay ninguna razón, dejar algo explícito
    if not razones:
        razones.append("Sin factores de riesgo detectados.")

    return PartRiskScore(
        part_id=part_id,
        tiempo_total=total_time,
        scrap_count=scrap_count,
        retrabajos=retrabajo_count,
        riesgo=min(riesgo, 1.0),
        razones=razones,
    )


# ======================== DETECCIÓN DE ANOMALÍAS ========================
@router.get("/anomalies")
def anomalies(
    db: Session = Depends(get_db),
    current_user=Depends(require_supervisor_or_admin),
):
    """
    Detecta piezas cuyo tiempo total de proceso está > 150% del promedio.
    Agrupa por part_id y suma los tiempos de todos los eventos.
    """
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
            "tiempo_total_seg": float(total_time),
            "porcentaje_sobre_promedio": round((float(total_time) / float(avg_time)) * 100, 2),
        }
        for part_id, total_time in rows
    ]
