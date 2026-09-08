"""
Modelo ORM para Grupos Académicos.
"""
from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from app.db.base import Base


class Grupo(Base):
    __tablename__ = "grupos_academicos"

    id = Column(Integer, primary_key=True, autoincrement=True)
    codigo_grupo = Column(String(30), nullable=False)  # ej: G1, G2
    materia_id = Column(Integer, ForeignKey("materias.id", ondelete="CASCADE"), nullable=False)
    profesor_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    cupo_maximo = Column(Integer, default=15, nullable=False)

    materia = relationship("Materia", back_populates="grupos")
    profesor = relationship("User", back_populates="grupos_docente")
    horarios = relationship("Horario", back_populates="grupo", cascade="all, delete-orphan")

    def to_dict(self):
        horarios_list = [h.to_dict() for h in self.horarios] if self.horarios else []
        horario_str = " / ".join([f"{h['dia']} {h['hora_inicio']}-{h['hora_fin']}" for h in horarios_list]) if horarios_list else "Sin horario asignado"
        aula_str = ", ".join(list(set([h['aula'] for h in horarios_list]))) if horarios_list else "Por definir"

        return {
            "id": self.id,
            "codigo_grupo": self.codigo_grupo,
            "codigo_seccion": f"{self.materia.codigo if self.materia else ''}-{self.codigo_grupo}",
            "nombre": self.materia.nombre if self.materia else self.codigo_grupo,
            "materia_id": self.materia_id,
            "materia_codigo": self.materia.codigo if self.materia else "",
            "materia_nombre": self.materia.nombre if self.materia else "",
            "carrera": self.materia.carrera if self.materia else "",
            "carrera_id": self.materia.carrera if self.materia else "",
            "nivel": self.materia.nivel if self.materia else 1,
            "tipo": self.materia.tipo if self.materia else "exclusiva",
            "profesor_id": self.profesor_id,
            "profesor_nombre": self.profesor.username if self.profesor else "Sin asignar",
            "docente": self.profesor.username if self.profesor else "Sin asignar",
            "cupo_maximo": self.cupo_maximo,
            "capacidad_aula": self.cupo_maximo,
            "inscritos": 0,
            "cupos_libres": self.cupo_maximo,
            "estado_aula": f"0/{self.cupo_maximo} Ocupados",
            "horario": horario_str,
            "aula": aula_str,
            "horarios": horarios_list
        }
