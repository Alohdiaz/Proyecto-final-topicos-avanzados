
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.station import Station
from app.schemas.station import StationCreate, StationOut, StationUpdate
from app.core.roles import require_admin, require_supervisor_or_admin, require_user

router = APIRouter(prefix="/stations", tags=["stations"])

# ------------------ CREAR ESTACIÓN (SOLO ADMIN) ------------------ #
@router.post("/", response_model=StationOut)
def create_station(
    station_in: StationCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_admin), 
):
    """
    Crea una nueva estación.
    Permitido para ADMIN.
    """

    # Revisa que no exista una estación con el mismo nombre (ejemplo de validación)
    existing = db.query(Station).filter(Station.nombre == station_in.nombre).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ya existe una estación con ese nombre.",
        )

    station = Station(**station_in.model_dump())
    db.add(station)
    db.commit()
    db.refresh(station)
    return station

# ------------------ LISTAR ESTACIONES (SUPERVISOR / ADMIN) ------------------ #
@router.get("/", response_model=list[StationOut])
def list_stations(
    db: Session = Depends(get_db),
    current_user=Depends(require_supervisor_or_admin),  
):
    """
    Lista todas las estaciones.
    Permitido para SUPERVISOR o ADMIN.
    """
    return db.query(Station).order_by(Station.id).all()

# ------------------ OBTENER ESTACIÓN POR ID ------------------ #
@router.get("/{station_id}", response_model=StationOut)
def get_station(
    station_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_user), 
):
    """
    Devuelve una estación por ID.
    Cualquier usuario autenticado puede verla.
    """
    station = db.query(Station).get(station_id)
    if not station:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Estación no encontrada.",
        )
    return station

# ------------------ ACTUALIZAR ESTACIÓN (SOLO ADMIN) ------------------ #
@router.patch("/{station_id}", response_model=StationOut)
def update_station(
    station_id: int,
    station_in: StationUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_admin),  
):
    """
    Actualiza una estación (parcial).
    Solo ADMIN.
    """
    station = db.query(Station).get(station_id)
    if not station:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Estación no encontrada.",
        )

    data = station_in.model_dump(exclude_unset=True)

    for field, value in data.items():
        setattr(station, field, value)

    db.add(station)
    db.commit()
    db.refresh(station)
    return station

# ------------------ ELIMINAR ESTACIÓN (SOLO ADMIN) ------------------ #
@router.delete("/{station_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_station(
    station_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_admin),  
):
    """
    Elimina una estación.
    Solo ADMIN.
    """
    station = db.query(Station).get(station_id)
    if not station:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Estación no encontrada.",
        )

    db.delete(station)
    db.commit()
    return None

# ------------------ RUTA PRIVADA (CUALQUIER ROL) ------------------ #
@router.get("/privado")
def privado(user=Depends(require_user)):  
    return {"mensaje": f"Hola {user.nombre}, tienes acceso."}
