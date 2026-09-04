"""
init_clean_db.py
================
Inicializa y limpia la base de datos dejando EXCLUSIVAMENTE el usuario Administrador de MBSystem:
- Usuario: admin
- Correo: admin@mbsystem.com
- Rol: admin

Elimina cualquier cuenta previa o predeterminada (admin_rector, docente_gomez, estudiante_garcia, Cristian).
"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.db.session import engine, SessionLocal
from app.db.base import Base
from app.models.user import User, RoleEnum
from app.models.token import RefreshToken
from app.models.login_history import LoginHistory
from app.core.security import hash_password

def init_clean_database():
    print("Depurando y recreando tablas de la base de datos...")
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        admin = User(
            username="admin",
            email="admin@mbsystem.com",
            hashed_password=hash_password("Contraseña123"),
            role=RoleEnum.admin,
            is_active=True
        )
        db.add(admin)
        db.commit()
        print("[OK] Base de datos depurada. Usuario Administrador de MBSystem creado:")
        print("     -> Usuario: admin | Correo: admin@mbsystem.com | Clave: Contraseña123")
    finally:
        db.close()

if __name__ == "__main__":
    init_clean_database()
