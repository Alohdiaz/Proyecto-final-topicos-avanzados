from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func
from app.db.base import Base


class Part(Base):
    __tablename__ = "parts"

    # ID autoincremental entero
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    serial = Column(String(50), unique=True, index=True, nullable=False)
    tipo_pieza = Column(String(50), nullable=False)
    lote = Column(String(50), nullable=True)
    # EN_PROCESO, OK, SCRAP, RETRABAJO
    status = Column(String(20), nullable=False, default="EN_PROCESO")
    fecha_creacion = Column(DateTime(timezone=True), server_default=func.now())
