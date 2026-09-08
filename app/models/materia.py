"""
Modelo ORM para Asignaturas / Materias.
"""
from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship
from app.db.base import Base


class Materia(Base):
    __tablename__ = "materias"

    id = Column(Integer, primary_key=True, autoincrement=True)
    codigo = Column(String(30), unique=True, index=True, nullable=False)
    nombre = Column(String(120), nullable=False)
    creditos = Column(Integer, default=3, nullable=False)
    carrera = Column(String(50), nullable=False)
    nivel = Column(Integer, default=1, nullable=False)
    tipo = Column(String(20), default="exclusiva", nullable=False)

    grupos = relationship("Grupo", back_populates="materia", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "codigo": self.codigo,
            "nombre": self.nombre,
            "creditos": self.creditos,
            "carrera": self.carrera,
            "carrera_id": self.carrera,
            "nivel": self.nivel,
            "tipo": self.tipo,
            "total_grupos": len(self.grupos) if self.grupos else 0
        }
