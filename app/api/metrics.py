from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.api import get_db
from app.models.part import Part
from app.models.trace_event import TraceEvent
from app.core.roles import require_supervisor_or_admin  

router = APIRouter(prefix="/metrics", tags=["metrics"])


@router.get("/parts-by-status")
def parts_by_status(
    db: Session = Depends(get_db),
    current_user=Depends(require_supervisor_or_admin),  
):
    rows = db.query(Part.status, func.count(Part.id)).group_by(Part.status).all()
    return {status: count for status, count in rows}


@router.get("/throughput")
def throughput(
    from_date: str,
    to_date: str,
    db: Session = Depends(get_db),
    current_user=Depends(require_supervisor_or_admin), 
):
    # piezas OK por día (usando trace_events con resultado OK)
    rows = (
        db.query(
            func.date(TraceEvent.timestamp_salida),
            func.count(TraceEvent.id),
        )
        .filter(TraceEvent.resultado == "OK")
        .filter(func.date(TraceEvent.timestamp_salida) >= from_date)
        .filter(func.date(TraceEvent.timestamp_salida) <= to_date)
        .group_by(func.date(TraceEvent.timestamp_salida))
        .order_by(func.date(TraceEvent.timestamp_salida))
        .all()
    )
    return [{"fecha": str(day), "piezas": count} for day, count in rows]


@router.get("/station-cycle-time")
def station_cycle_time(
    db: Session = Depends(get_db),
    current_user=Depends(require_supervisor_or_admin), 
):
    # promedio en segundos del ciclo por estación
    rows = (
        db.query(
            TraceEvent.station_id,
            func.avg(
                func.extract(
                    "epoch",
                    TraceEvent.timestamp_salida - TraceEvent.timestamp_entrada,
                )
            ),
        )
        .group_by(TraceEvent.station_id)
        .all()
    )
    return [
        {
            "station_id": station_id,
            "tiempo_promedio_segundos": float(avg_secs) if avg_secs else None,
        }
        for station_id, avg_secs in rows
    ]


@router.get("/scrap-rate")
def scrap_rate(
    db: Session = Depends(get_db),
    current_user=Depends(require_supervisor_or_admin),  
):
    # porcentaje de SCRAP por tipo_pieza
    total_by_type = (
        db.query(Part.tipo_pieza, func.count(Part.id))
        .group_by(Part.tipo_pieza)
        .all()
    )
    scrap_by_type = (
        db.query(Part.tipo_pieza, func.count(Part.id))
        .filter(Part.status == "SCRAP")
        .group_by(Part.tipo_pieza)
        .all()
    )

    total_dict = {t: c for t, c in total_by_type}
    scrap_dict = {t: c for t, c in scrap_by_type}

    result = []
    for tipo, total in total_dict.items():
        scrap = scrap_dict.get(tipo, 0)
        rate = scrap / total if total > 0 else 0
        result.append({"tipo_pieza": tipo, "scrap_rate": rate})
    return result
