# app/api/trace_events.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime

from app.db.session import get_db
from app.models.trace_event import TraceEvent
from app.models.part import Part
from app.models.station import Station
from app.schemas.trace_event import TraceEventCreate, TraceEventOut
from app.core.roles import require_user, require_supervisor_or_admin

router = APIRouter(prefix="/trace-events", tags=["trace_events"])


# ======================== FUNCIÓN AUXILIAR PARA CALCULAR RISK SCORE ========================
def calculate_risk_score_for_part(part_id: int, db: Session) -> dict:
    """
    Función auxiliar para calcular el risk score de una pieza
    Retorna un diccionario con el riesgo, nivel y razones
    """
    part = db.query(Part).filter(Part.id == part_id).first()
    if not part:
        return None
    
    # Obtener todos los eventos de la pieza
    events = db.query(TraceEvent).filter(TraceEvent.part_id == part_id).all()
    
    if not events:
        return {
            "riesgo": 0.0,
            "nivel": "BAJO",
            "razones": ["Sin eventos registrados"],
            "detalles": {
                "tiempo_total_segundos": 0,
                "tiempo_total_minutos": 0,
                "eventos_totales": 0,
                "scrap_count": 0,
                "retrabajo_count": 0
            }
        }
    
    # Calcular tiempo total
    total_time = 0
    eventos_con_tiempo = 0
    for ev in events:
        if ev.timestamp_entrada and ev.timestamp_salida:
            delta = (ev.timestamp_salida - ev.timestamp_entrada).total_seconds()
            total_time += delta
            eventos_con_tiempo += 1
    
    # Contar resultados
    scrap_count = sum(1 for ev in events if ev.resultado == "SCRAP")
    retrabajo_count = sum(1 for ev in events if ev.resultado == "RETRABAJO")
    
    # Inicializar riesgo
    riesgo = 0.0
    razones = []
    
    # Factor 1: Evaluación de tiempo total
    if total_time > 900:  # Más de 15 minutos
        riesgo += 0.4
        razones.append(f"Tiempo total elevado ({round(total_time/60, 1)} min > 15 min)")
    elif total_time > 600:  # Más de 10 minutos
        riesgo += 0.2
        razones.append(f"Tiempo sobre promedio ({round(total_time/60, 1)} min > 10 min)")
    
    # Factor 2: Evaluación de SCRAP
    if scrap_count > 0:
        riesgo += 0.4
        razones.append(f"Historial de SCRAP ({scrap_count} evento{'s' if scrap_count > 1 else ''})")
    
    # Factor 3: Evaluación de retrabajos
    if retrabajo_count >= 2:
        riesgo += 0.2
        razones.append(f"Múltiples retrabajos ({retrabajo_count} eventos)")
    elif retrabajo_count == 1:
        riesgo += 0.1
        razones.append("Un retrabajo registrado")
    
    # Limitar riesgo entre 0 y 1
    riesgo = min(riesgo, 1.0)
    
    # Determinar nivel de riesgo
    if riesgo >= 0.7:
        nivel = "ALTO"
    elif riesgo >= 0.4:
        nivel = "MEDIO"
    else:
        nivel = "BAJO"
    
    # Si no hay razones, significa que está todo bien
    if not razones:
        razones.append("Sin factores de riesgo detectados")
    
    return {
        "riesgo": round(riesgo, 2),
        "nivel": nivel,
        "razones": razones,
        "detalles": {
            "tiempo_total_segundos": round(total_time, 2),
            "tiempo_total_minutos": round(total_time / 60, 2),
            "eventos_totales": len(events),
            "scrap_count": scrap_count,
            "retrabajo_count": retrabajo_count
        }
    }


# ======================== CREAR EVENTO DE TRAZA ========================
@router.post("/", response_model=TraceEventOut)
def create_trace_event(
    event_in: TraceEventCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_user),
):
    """
    Crea un nuevo evento de traza para una pieza.
    Calcula automáticamente el risk score después de crear el evento.
    """
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

    # NOTA: Comenté esta validación para permitir múltiples eventos por pieza
    # Si quieres mantenerla, descomenta estas líneas:
    # existing_event = db.query(TraceEvent).filter(TraceEvent.part_id == event_in.part_id).first()
    # if existing_event:
    #     raise HTTPException(
    #         status_code=status.HTTP_400_BAD_REQUEST,
    #         detail="Ya existe un evento registrado para esta pieza.",
    #     )

    # Actualizar el estado de la pieza si el resultado es válido
    if event_in.resultado in {"OK", "SCRAP", "RETRABAJO"}:
        part.status = event_in.resultado
        db.add(part)
        
        # Si es SCRAP o RETRABAJO, establecer timestamp_salida automáticamente si no existe
        if event_in.resultado in {"SCRAP", "RETRABAJO"} and not event_in.timestamp_salida:
            event_in.timestamp_salida = datetime.utcnow()

    # Crear el evento de traza
    event = TraceEvent(**event_in.model_dump())
    db.add(event)
    
    # Guardar en la base de datos
    db.commit()
    db.refresh(event)
    
    # IMPORTANTE: Calcular el risk score DESPUÉS de crear el evento
    risk_score = calculate_risk_score_for_part(event_in.part_id, db)
    
    # Crear un diccionario con el evento y el risk score
    event_dict = {
        "id": event.id,
        "part_id": event.part_id,
        "station_id": event.station_id,
        "timestamp_entrada": event.timestamp_entrada,
        "timestamp_salida": event.timestamp_salida,
        "resultado": event.resultado,
        "operador_id": event.operador_id,
        "observaciones": event.observaciones,
        "risk_score": risk_score  # Agregar risk score a la respuesta
    }
    
    return event_dict


# ======================== HISTORIAL COMPLETO DE UNA PIEZA ========================
@router.get("/part/{part_id}")
def list_trace_events_for_part(
    part_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_supervisor_or_admin),
):
    """
    Obtiene el historial completo de eventos de una pieza.
    Incluye el risk score actual de la pieza.
    """
    # Verificar que la pieza existe
    part = db.query(Part).filter(Part.id == part_id).first()
    if not part:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pieza no encontrada.",
        )
    
    # Obtener eventos ordenados por fecha
    events = (
        db.query(TraceEvent)
        .filter(TraceEvent.part_id == part_id)
        .order_by(TraceEvent.timestamp_entrada.asc())
        .all()
    )
    
    if not events:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No hay eventos para esa pieza.",
        )
    
    # Calcular el risk score actual
    risk_score = calculate_risk_score_for_part(part_id, db)
    
    # Formatear eventos para la respuesta
    events_list = [
        {
            "id": e.id,
            "part_id": e.part_id,
            "station_id": e.station_id,
            "timestamp_entrada": e.timestamp_entrada,
            "timestamp_salida": e.timestamp_salida,
            "resultado": e.resultado,
            "operador_id": e.operador_id,
            "observaciones": e.observaciones
        }
        for e in events
    ]
    
    # Retornar historial completo con risk score
    return {
        "part_id": part_id,
        "tipo_pieza": part.tipo_pieza,
        "lote": part.lote,
        "status": part.status,
        "fecha_creacion": part.fecha_creacion,
        "total_eventos": len(events),
        "eventos": events_list,
        "risk_score": risk_score  # Incluir risk score en la respuesta
    }


# ======================== OBTENER RISK SCORE DE UNA PIEZA ========================
@router.get("/part/{part_id}/risk-score")
def get_part_risk_score(
    part_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_user),
):
    """
    Endpoint dedicado para obtener solo el risk score de una pieza.
    Útil para consultas rápidas sin obtener todo el historial.
    """
    # Verificar que la pieza existe
    part = db.query(Part).filter(Part.id == part_id).first()
    if not part:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pieza no encontrada.",
        )
    
    # Calcular risk score
    risk_score = calculate_risk_score_for_part(part_id, db)
    
    return {
        "part_id": part_id,
        "tipo_pieza": part.tipo_pieza,
        "lote": part.lote,
        "status": part.status,
        **risk_score  # Expandir el diccionario de risk_score
    }


# ======================== CERRAR/ACTUALIZAR UN EVENTO ========================
@router.put("/{event_id}/close")
def close_trace_event(
    event_id: int,
    resultado: str,
    observaciones: str = None,
    db: Session = Depends(get_db),
    current_user=Depends(require_user)
):
    """
    Cierra un evento de traza estableciendo timestamp_salida y resultado.
    Recalcula automáticamente el risk score.
    """
    # Validar resultado
    if resultado not in ["OK", "SCRAP", "RETRABAJO"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Resultado debe ser OK, SCRAP o RETRABAJO"
        )
    
    # Buscar el evento
    event = db.query(TraceEvent).filter(TraceEvent.id == event_id).first()
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evento no encontrado"
        )
    
    # Actualizar evento
    event.timestamp_salida = datetime.utcnow()
    event.resultado = resultado
    if observaciones:
        event.observaciones = observaciones
    
    # Actualizar estado de la pieza
    part = db.query(Part).filter(Part.id == event.part_id).first()
    if part:
        part.status = resultado
        db.add(part)
    
    db.add(event)
    db.commit()
    db.refresh(event)
    
    # Recalcular risk score
    risk_score = calculate_risk_score_for_part(event.part_id, db)
    
    return {
        "message": "Evento cerrado exitosamente",
        "event": {
            "id": event.id,
            "part_id": event.part_id,
            "station_id": event.station_id,
            "timestamp_entrada": event.timestamp_entrada,
            "timestamp_salida": event.timestamp_salida,
            "resultado": event.resultado,
            "observaciones": event.observaciones
        },
        "risk_score": risk_score
    }