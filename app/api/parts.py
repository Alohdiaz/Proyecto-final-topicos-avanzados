from datetime import date
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.part import Part
from app.schemas.part import PartCreate, PartOut, PartUpdate
from app.core.roles import (
    require_user,
    require_supervisor_or_admin,
    require_operator_or_admin,
    require_admin,
)

router = APIRouter(prefix="/parts", tags=["parts"])


# ------------------ CREAR PIEZA (OPERATOR / ADMIN) ------------------ #
@router.post("/", response_model=PartOut)
def create_part(
    part_in: PartCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_operator_or_admin),
):
    """
    Crea una nueva pieza.
    Permitido para OPERATOR o ADMIN.
    """

    # Validar serial único
    existing = db.query(Part).filter(Part.serial == part_in.serial).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El serial ya existe.",
        )

    part = Part(**part_in.model_dump())
    db.add(part)
    db.commit()
    db.refresh(part)
    return part


# -------- LISTAR PIEZAS (SUPERVISOR / ADMIN) + filtros ------------- #
@router.get("/", response_model=list[PartOut])
def list_parts(
    status: str | None = None,
    tipo_pieza: str | None = None,
    lote: str | None = None,
    fecha_desde: date | None = None,
    fecha_hasta: date | None = None,
    db: Session = Depends(get_db),
    current_user=Depends(require_supervisor_or_admin),
):
    """
    Lista piezas con filtros opcionales:
    - status
    - tipo_pieza
    - lote
    - rango de fechas (fecha_creacion entre fecha_desde y fecha_hasta)
    Permitido para SUPERVISOR o ADMIN.
    """
    query = db.query(Part)

    if status:
        query = query.filter(Part.status == status)

    if tipo_pieza:
        query = query.filter(Part.tipo_pieza == tipo_pieza)

    if lote:
        query = query.filter(Part.lote == lote)

    if fecha_desde:
        query = query.filter(Part.fecha_creacion >= fecha_desde)

    if fecha_hasta:
        query = query.filter(Part.fecha_creacion <= fecha_hasta)

    return query.order_by(Part.id).all()


# ------ OBTENER PIEZA POR ID (OPERATOR / SUPERVISOR / ADMIN) ------- #
@router.get("/{part_id}", response_model=PartOut)
def get_part(
    part_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_user),
):
    """
    Devuelve una pieza por ID.
    Cualquier usuario autenticado puede verla.
    """
    part = db.query(Part).get(part_id)
    if not part:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pieza no encontrada.",
        )
    return part


# ---------- ACTUALIZAR PIEZA (solo ADMIN) -------------------------- #
@router.patch("/{part_id}", response_model=PartOut)
def update_part(
    part_id: int,
    part_in: PartUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_admin),
):
    """
    Actualiza una pieza (parcial).
    Solo ADMIN.
    """
    part = db.query(Part).get(part_id)
    if not part:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pieza no encontrada.",
        )

    data = part_in.model_dump(exclude_unset=True)

    # si quieren cambiar el serial, validar que no se repita
    if "serial" in data:
        existing = (
            db.query(Part)
            .filter(Part.serial == data["serial"], Part.id != part_id)
            .first()
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Ya existe otra pieza con ese serial.",
            )

    for field, value in data.items():
        setattr(part, field, value)

    db.add(part)
    db.commit()
    db.refresh(part)
    return part


# ---------- ELIMINAR PIEZA (solo ADMIN) ---------------------------- #
@router.delete("/{part_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_part(
    part_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_admin),
):
    """
    Elimina una pieza.
    Solo ADMIN.
    """
    part = db.query(Part).get(part_id)
    if not part:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pieza no encontrada.",
        )

    db.delete(part)
    db.commit()
    return None
