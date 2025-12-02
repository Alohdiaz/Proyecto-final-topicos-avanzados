# app/api/trace_events.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.trace_event import TraceEvent
from app.models.part import Part
from app.models.station import Station
from app.schemas.trace_event import TraceEventCreate, TraceEventOut
from app.core.roles import require_user, require_supervisor_or_admin

router = APIRouter(prefix="/trace-events", tags=["trace_events"])


# --------- Crear evento de traza (OPERADOR / SUPERVISOR / ADMIN) ---------

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

    event = TraceEvent(**event_in.model_dump())
    db.add(event)

    # Opcional: actualizar status actual de la pieza
    # part.status = event_in.status_nuevo
    # db.add(part)

    db.commit()
    db.refresh(event)
    return event


# --------- Historial completo de una pieza (SUPERVISOR / ADMIN) ---------

@router.get("/part/{part_id}", response_model=list[TraceEventOut])
def list_trace_events_for_part(
    part_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(require_supervisor_or_admin),
):
    events = (
        db.query(TraceEvent)
        .filter(TraceEvent.part_id == part_id)
        .order_by(TraceEvent.timestamp_entrada.asc())
        .all()
    )
    if not events:
        # Devuelve 404 si no hay eventos para esa pieza
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No hay eventos para esa pieza.",
        )
    return events
