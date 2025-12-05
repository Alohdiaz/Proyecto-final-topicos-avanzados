from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.part import Part
from app.models.trace_event import TraceEvent
from app.core.roles import require_supervisor_or_admin

router = APIRouter(prefix="/metrics", tags=["metrics"])

# ---------------------- PARTS BY STATUS ---------------------- #
@router.get("/parts-by-status")
def parts_by_status(
    db: Session = Depends(get_db),
    current_user=Depends(require_supervisor_or_admin),
):
    """
    Devuelve un conteo de piezas por status.
    Requiere rol SUPERVISOR o ADMIN.
    """
    rows = (
        db.query(Part.status, func.count(Part.id))
        .group_by(Part.status)
        .all()
    )
    return {status: count for status, count in rows}


# ---------------------- THROUGHPUT --------------------------- #
@router.get("/throughput")
def throughput(
    from_date: str,
    to_date: str,
    db: Session = Depends(get_db),
    current_user=Depends(require_supervisor_or_admin),
):
    """
    Devuelve piezas OK por día entre from_date y to_date (YYYY-MM-DD).
    Usa los TraceEvent con resultado OK y timestamp_salida no nulo.
    """
    try:
        from_date_obj = datetime.strptime(from_date, "%Y-%m-%d").date()
        to_date_obj = datetime.strptime(to_date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Formato de fecha incorrecto. Usa YYYY-MM-DD.",
        )

    rows = (
        db.query(
            func.date(TraceEvent.timestamp_salida),
            func.count(TraceEvent.id),
        )
        .filter(TraceEvent.resultado == "OK")
        .filter(TraceEvent.timestamp_salida.isnot(None))
        .filter(func.date(TraceEvent.timestamp_salida) >= from_date_obj)
        .filter(func.date(TraceEvent.timestamp_salida) <= to_date_obj)
        .group_by(func.date(TraceEvent.timestamp_salida))
        .order_by(func.date(TraceEvent.timestamp_salida))
        .all()
    )

    return [{"fecha": str(day), "piezas": count} for day, count in rows]


# ------------------- STATION CYCLE TIME ---------------------- #
@router.get("/station-cycle-time")
def station_cycle_time(
    db: Session = Depends(get_db),
    current_user=Depends(require_supervisor_or_admin),
):
    """
    Devuelve el tiempo de ciclo promedio (en segundos) por estación.
    Calculado como timestamp_salida - timestamp_entrada.
    """
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
        .filter(TraceEvent.timestamp_salida.isnot(None))
        .filter(TraceEvent.timestamp_entrada.isnot(None))
        .group_by(TraceEvent.station_id)
        .all()
    )

    return [
        {
            "station_id": station_id,
            "tiempo_promedio_segundos": float(avg_secs) if avg_secs is not None else None,
        }
        for station_id, avg_secs in rows
    ]


# ----------------------- SCRAP RATE -------------------------- #
@router.get("/scrap-rate")
def scrap_rate(
    db: Session = Depends(get_db),
    current_user=Depends(require_supervisor_or_admin),
):
    """
    Devuelve el porcentaje de SCRAP por tipo de pieza.
    scrap_rate va de 0 a 1 (0% a 100%).
    """
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
        rate = float(scrap) / float(total) if total > 0 else 0.0
        result.append({"tipo_pieza": tipo, "scrap_rate": rate})

    return result
