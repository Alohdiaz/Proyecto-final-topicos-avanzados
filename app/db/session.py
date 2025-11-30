from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from app.core.config import settings

# Crear el engine con la URL de la base de datos
engine = create_engine(
    settings.DATABASE_URL,
    future=True,
)

# Factoría de sesiones
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

def get_db() -> Generator[Session, None, None]:
    """
    Dependencia para FastAPI.
    Crea una sesión por petición y la cierra al final.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
