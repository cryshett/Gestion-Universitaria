"""
Modelo ORM para Horarios de Clases y Aulas.
"""
from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from app.db.base import Base


class Horario(Base):
    __tablename__ = "horarios_academicos"

    id = Column(Integer, primary_key=True, autoincrement=True)
    grupo_id = Column(Integer, ForeignKey("grupos_academicos.id", ondelete="CASCADE"), nullable=False)
    dia = Column(String(20), nullable=False)  # Lunes, Martes, etc.
    hora_inicio = Column(String(10), nullable=False)  # 07:00
    hora_fin = Column(String(10), nullable=False)     # 09:00
    aula = Column(String(60), nullable=False)         # Aula 101
    edificio = Column(String(60), default="Edificio Central")

    grupo = relationship("Grupo", back_populates="horarios")

    def to_dict(self):
        materia = self.grupo.materia if self.grupo else None
        profesor = self.grupo.profesor if self.grupo else None

        return {
            "id": self.id,
            "grupo_id": self.grupo_id,
            "grupo_nombre": self.grupo.codigo_grupo if self.grupo else "",
            "materia_id": materia.id if materia else None,
            "materia_codigo": materia.codigo if materia else "",
            "materia_nombre": materia.nombre if materia else "",
            "carrera": materia.carrera if materia else "",
            "carrera_id": materia.carrera if materia else "",
            "nivel": materia.nivel if materia else 1,
            "profesor_id": profesor.id if profesor else None,
            "profesor_nombre": profesor.username if profesor else "Docente sin asignar",
            "dia": self.dia,
            "dia_semana": self.dia,
            "hora_inicio": self.hora_inicio,
            "hora_fin": self.hora_fin,
            "aula": self.aula,
            "edificio": self.edificio
        }
