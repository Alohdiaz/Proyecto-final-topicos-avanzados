from sqlalchemy import Column, Integer, String
from app.db.base import Base

class Station(Base):
    __tablename__ = "stations"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(100), nullable=False)
    tipo = Column(String(50), nullable=False)   # inspección, ensamble, prueba, etc.
    linea = Column(String(50), nullable=True)
