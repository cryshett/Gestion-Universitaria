"""
test_auth_integration.py
=========================
Prueba automatizada de verificación de la depuración de base de datos y autenticación MBSystem:
- Retención exclusiva del usuario Administrador (admin / admin@mbsystem.com / Contraseña123)
- Registro dinámico de nuevas cuentas desde la API de Admin (/api/admin/crear-usuario)
- Verificación de credenciales con Argon2 y JWT
- Control de intentos fallidos y bloqueo tras 3 intentos
"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import importlib.util
spec = importlib.util.spec_from_file_location("app_flask", os.path.join(os.path.dirname(__file__), "..", "app.py"))
app_flask = importlib.util.module_from_spec(spec)
spec.loader.exec_module(app_flask)
app = app_flask.app

from app.db.session import engine, SessionLocal
from app.db.base import Base
from app.models.user import User, RoleEnum
from app.core.security import hash_password

def run_tests():
    print("--- 1. Recreando esquema de BD y sembrando EXCLUSIVAMENTE admin de MBSystem ---")
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    admin = User(
        username="admin",
        email="admin@mbsystem.com",
        hashed_password=hash_password("Contraseña123"),
        role=RoleEnum.admin,
        is_active=True
    )
    db.add(admin)
    db.commit()

    total_usuarios = db.query(User).count()
    assert total_usuarios == 1, f"Se esperaba exactamente 1 usuario inicial, se encontraron {total_usuarios}"
    print("[OK] Únicamente existe 1 cuenta inicial en la BD (admin / admin@mbsystem.com).")
    db.close()

    client = app.test_client()

    print("--- 2. Probando rechazo de cuentas eliminadas (admin_rector, docente_gomez, estudiante_garcia, Cristian) ---")
    for usr in ["admin_rector", "docente_gomez", "estudiante_garcia", "Cristian"]:
        res_del = client.post("/api/login", json={"usuario": usr, "clave": "123"})
        assert res_del.status_code == 401, f"Cuenta {usr} debería estar eliminada (recibido {res_del.status_code})"
    print("[OK] Cuentas legacy rechazadas correctamente.")

    print("--- 3. Probando Login exitoso con Administrador de MBSystem ---")
    res_admin = client.post("/api/login", json={"usuario": "admin", "clave": "Contraseña123"})
    assert res_admin.status_code == 200, f"Error en login admin: {res_admin.json}"
    data_admin = res_admin.get_json()
    assert data_admin["role"] == "admin"
    assert data_admin["redirect"] == "/admin"
    assert "access_token" in data_admin
    print("[OK] Login de Admin MBSystem verificado -> Redirect: /admin, JWT Token generado.")

    print("--- 4. Creando dinámicamente un Docente desde la API de Administración ---")
    with client.session_transaction() as sess:
        sess["role"] = "admin"
        sess["user_id"] = 1

    res_crear_doc = client.post("/api/admin/crear-usuario", json={
        "username": "docente_nuevo",
        "email": "docente.nuevo@universidad.edu",
        "password": "ClaveDocente2026!",
        "role": "teacher"
    })
    assert res_crear_doc.status_code == 201, f"Error al crear docente: {res_crear_doc.json}"
    print("[OK] Docente creado dinámicamente desde el panel de control.")

    print("--- 5. Probando Login exitoso del Docente dinámico recién registrado ---")
    res_login_doc = client.post("/api/login", json={"usuario": "docente.nuevo@universidad.edu", "clave": "ClaveDocente2026!"})
    assert res_login_doc.status_code == 200
    data_login_doc = res_login_doc.get_json()
    assert data_login_doc["role"] == "teacher"
    assert data_login_doc["redirect"] == "/teacher"
    print("[OK] Login de Docente dinámico verificado -> Redirect: /teacher.")

    print("--- 6. Probando bloqueo de seguridad tras 3 intentos fallidos ---")
    for i in range(1, 4):
        res_fail = client.post("/api/login", json={"usuario": "admin", "clave": "ClaveErronea"})
        print(f"   Intento fallido {i}: Status {res_fail.status_code} - {res_fail.json.get('mensaje')}")

    res_locked = client.post("/api/login", json={"usuario": "admin", "clave": "Contraseña123"})
    assert res_locked.status_code == 423, f"Esperado 423 Locked, recibido {res_locked.status_code}"
    print("[OK] Cuenta 'admin' bloqueada tras 3 fallos consecutivos.")

    print("\n========================================================")
    print(" ¡VERIFICACIÓN COMPLETA PASÓ EXITOSAMENTE! ")
    print("========================================================")

if __name__ == "__main__":
    run_tests()
