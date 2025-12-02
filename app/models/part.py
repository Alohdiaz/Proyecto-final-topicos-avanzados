from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func
from app.db.base import Base

class Part(Base):
    __tablename__ = "parts"

    id = Column(String, primary_key=True, index=True)
    serial = Column(String(50), unique=True, index=True, nullable=False)
    tipo_pieza = Column(String(50), nullable=False)
    lote = Column(String(50), nullable=True)
    status = Column(String(20), nullable=False, default="EN_PROCESO")  # EN_PROCESO, OK, SCRAP, RETRABAJO
    fecha_creacion = Column(DateTime(timezone=True), server_default=func.now())
