from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base import Base

class TraceEvent(Base):
    __tablename__ = "trace_events"

    id = Column(Integer, primary_key=True, index=True)
    part_id = Column(Integer, ForeignKey("parts.id"), nullable=False)
    station_id = Column(Integer, ForeignKey("stations.id"), nullable=False)
    operador_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    timestamp_entrada = Column(DateTime(timezone=True), server_default=func.now())
    timestamp_salida = Column(DateTime(timezone=True), nullable=True)

    resultado = Column(String(20), nullable=False)  # OK, SCRAP, RETRABAJO
    observaciones = Column(String(255), nullable=True)

    part = relationship("Part")
    station = relationship("Station")
    operador = relationship("User")
