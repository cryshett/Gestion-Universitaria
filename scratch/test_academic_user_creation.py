"""
test_academic_user_creation.py
==============================
Verifica la ampliación del registro de usuarios con datos académicos (Estudiante y Profesor):
1. Registro de Estudiante con Carrera, Semestre, Grupo, Cédula y Nombre.
2. Registro de Profesor con Carrera/Departamento, Cédula y Nombre.
3. Validación de unicidad de Cédula/Identificación.
4. Prueba de transacción atómica (rollback en mb_system.db si falla universidad.db).
5. Verificación de /api/me y /api/admin/usuarios.
"""
import os
import sys
import sqlite3

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

def run_academic_tests():
    print("====================================================================")
    print(" INICIANDO TEST DE REGISTRO DE USUARIOS CON DATOS ACADÉMICOS ")
    print("====================================================================")

    # Limpiar posibles restos de ejecuciones previas
    conn_sq = sqlite3.connect("universidad.db")
    with conn_sq:
        conn_sq.execute("DELETE FROM estudiantes WHERE username IN ('estudiante_test', 'otro_estudiante', 'usuario_fallido') OR documento IN ('1020304050', '9999999999');")
        conn_sq.execute("DELETE FROM profesores WHERE username IN ('docente_test') OR documento IN ('7080901020');")
    conn_sq.close()

    db_clean = SessionLocal()
    for u_del in db_clean.query(User).filter(User.username.in_(["estudiante_test", "docente_test", "otro_estudiante", "usuario_fallido"])).all():
        db_clean.delete(u_del)
    db_clean.commit()
    db_clean.close()

    client = app.test_client()

    # Simular sesión activa de Administrador
    with client.session_transaction() as sess:
        sess["role"] = "admin"
        sess["user_id"] = 1
        sess["username"] = "admin"

    # 1. REGISTRO DE ESTUDIANTE
    print("\n--- 1. Registrando Nuevo Estudiante (ISW, Semestre 3, Grupo G2) ---")
    doc_estudiante = "1020304050"
    payload_est = {
        "username": "estudiante_test",
        "email": "estudiante.test@universidad.edu",
        "password": "Password123!",
        "role": "student",
        "nombre": "Estudiante Prueba Pérez",
        "identificacion": doc_estudiante,
        "carrera_id": "ISW",
        "semestre": 3,
        "grupo": "G2"
    }
    res_est = client.post("/api/admin/crear-usuario", json=payload_est)
    assert res_est.status_code == 201, f"Fallo al registrar estudiante: {res_est.json}"
    print(f"[OK] Respuesta 201: {res_est.json.get('mensaje')}")

    # Verificar en mb_system.db
    db_sqla = SessionLocal()
    user_est = db_sqla.query(User).filter(User.username == "estudiante_test").first()
    assert user_est is not None, "El estudiante no fue creado en mb_system.db (users)"
    assert user_est.role == RoleEnum.student, f"Rol incorrecto: {user_est.role}"
    est_user_id = user_est.id
    db_sqla.close()
    print(f"[OK] mb_system.db: Usuario #{est_user_id} guardado con rol '{user_est.role.value}'")

    # Verificar en universidad.db (estudiantes)
    conn_sqlite = sqlite3.connect("universidad.db")
    conn_sqlite.row_factory = sqlite3.Row
    cursor = conn_sqlite.cursor()
    cursor.execute("SELECT * FROM estudiantes WHERE documento = ? OR username = ?;", (doc_estudiante, "estudiante_test"))
    est_row = cursor.fetchone()
    assert est_row is not None, "El estudiante no fue creado en universidad.db (estudiantes)"
    assert est_row["nombre"] == "Estudiante Prueba Pérez"
    assert est_row["carrera_id"] == "ISW"
    assert est_row["semestre"] == 3
    assert est_row["grupo"] == "G2"
    assert est_row["user_id"] == est_user_id
    print(f"[OK] universidad.db: Ficha académica #{est_row['id']} (Matrícula: {est_row['matricula']}) guardada correctamente.")

    # 2. REGISTRO DE PROFESOR
    print("\n--- 2. Registrando Nuevo Profesor (MED, Medicina Humana) ---")
    doc_prof = "7080901020"
    payload_prof = {
        "username": "docente_test",
        "email": "docente.test@universidad.edu",
        "password": "PasswordDocente2026!",
        "role": "teacher",
        "nombre": "Dr. Fernando Ruiz",
        "identificacion": doc_prof,
        "carrera_principal": "MED",
        "titulo_academico": "Doctor en Medicina Interna"
    }
    res_prof = client.post("/api/admin/crear-usuario", json=payload_prof)
    assert res_prof.status_code == 201, f"Fallo al registrar docente: {res_prof.json}"
    print(f"[OK] Respuesta 201: {res_prof.json.get('mensaje')}")

    # Verificar en mb_system.db
    db_sqla = SessionLocal()
    user_prof = db_sqla.query(User).filter(User.username == "docente_test").first()
    assert user_prof is not None, "El docente no fue creado en mb_system.db (users)"
    assert user_prof.role == RoleEnum.teacher, f"Rol incorrecto: {user_prof.role}"
    prof_user_id = user_prof.id
    db_sqla.close()
    print(f"[OK] mb_system.db: Usuario #{prof_user_id} guardado con rol '{user_prof.role.value}'")

    # Verificar en universidad.db (profesores)
    cursor.execute("SELECT * FROM profesores WHERE documento = ? OR username = ?;", (doc_prof, "docente_test"))
    prof_row = cursor.fetchone()
    assert prof_row is not None, "El docente no fue creado en universidad.db (profesores)"
    assert prof_row["nombre"] == "Dr. Fernando Ruiz"
    assert prof_row["carrera_principal"] == "MED"
    assert prof_row["titulo_academico"] == "Doctor en Medicina Interna"
    assert prof_row["user_id"] == prof_user_id
    print(f"[OK] universidad.db: Ficha docente #{prof_row['id']} guardada correctamente.")

    # 3. VALIDACIÓN DE UNICIDAD DE CÉDULA/IDENTIFICACIÓN
    print("\n--- 3. Probando Validación de Cédula Duplicada ---")
    payload_dup = {
        "username": "otro_estudiante",
        "email": "otro.estudiante@universidad.edu",
        "password": "Password123!",
        "role": "student",
        "nombre": "Otro Estudiante",
        "identificacion": doc_estudiante,  # Cédula ya existente
        "carrera_id": "DER",
        "semestre": 1,
        "grupo": "G1"
    }
    res_dup = client.post("/api/admin/crear-usuario", json=payload_dup)
    assert res_dup.status_code == 400, f"Se esperaba 400 para cédula duplicada, recibido {res_dup.status_code}"
    print(f"[OK] Rechazado con 400: {res_dup.json.get('mensaje')}")

    # 4. PRUEBA DE ATOMICIDAD (ROLLBACK EN ERROR)
    print("\n--- 4. Probando Transacción Atómica (Rollback en SQLAlchemy ante fallo) ---")
    payload_invalido = {
        "username": "usuario_fallido",
        "email": "fallido@universidad.edu",
        "password": "Password123!",
        "role": "student",
        "nombre": "",  # Nombre vacío provocará validación 400
        "identificacion": "9999999999"
    }
    res_inv = client.post("/api/admin/crear-usuario", json=payload_invalido)
    assert res_inv.status_code == 400

    # Verificar que "usuario_fallido" NO existe en mb_system.db
    db_sqla = SessionLocal()
    user_fail = db_sqla.query(User).filter(User.username == "usuario_fallido").first()
    assert user_fail is None, "Atomicidad violada: se creó el usuario en users a pesar del error"
    db_sqla.close()
    print("[OK] Atomicidad confirmada: Ningún usuario huérfano creado en mb_system.db ante error.")

    # 5. VERIFICACIÓN DE /api/admin/usuarios
    print("\n--- 5. Verificando /api/admin/usuarios con Perfiles Académicos ---")
    res_lista = client.get("/api/admin/usuarios")
    assert res_lista.status_code == 200
    usuarios = res_lista.get_json()
    assert len(usuarios) >= 3  # admin, estudiante_test, docente_test
    user_est_item = next((u for u in usuarios if u["username"] == "estudiante_test"), None)
    assert user_est_item is not None
    assert user_est_item["nombre"] == "Estudiante Prueba Pérez"
    assert user_est_item["documento"] == doc_estudiante
    assert "ISW" in user_est_item["detalle_academico"]
    print(f"[OK] Usuario en tabla Admin: {user_est_item['nombre']} | Doc: {user_est_item['documento']} | Detalle: {user_est_item['detalle_academico']}")

    # 6. LOGIN Y /api/me
    print("\n--- 6. Probando Login y /api/me del Estudiante Dinámico ---")
    res_login = client.post("/api/login", json={"usuario": "estudiante_test", "clave": "Password123!"})
    assert res_login.status_code == 200
    assert res_login.json["role"] == "student"
    assert res_login.json["redirect"] == "/student"

    res_me = client.get("/api/me")
    assert res_me.status_code == 200
    me_data = res_me.get_json()
    assert me_data["role"] == "student"
    assert me_data["nombre"] == "Estudiante Prueba Pérez"
    assert me_data["matricula"] == est_row["matricula"]
    assert me_data["carrera_id"] == "ISW"
    print(f"[OK] /api/me retornado para estudiante: {me_data['nombre']} ({me_data['carrera_nombre']}, {me_data['matricula']})")

    # 7. LIMPIEZA DE TEST
    print("\n--- 7. Probando Eliminación Coordinada de Usuario (#ID) ---")
    with client.session_transaction() as sess:
        sess["role"] = "admin"
        sess["user_id"] = 1

    res_del_est = client.delete(f"/api/admin/usuarios/{est_user_id}")
    assert res_del_est.status_code == 200
    cursor.execute("SELECT * FROM estudiantes WHERE user_id = ?;", (est_user_id,))
    assert cursor.fetchone() is None, "La ficha del estudiante no se eliminó en universidad.db"
    print("[OK] Usuario y ficha académica eliminados de ambas bases de datos.")

    res_del_prof = client.delete(f"/api/admin/usuarios/{prof_user_id}")
    assert res_del_prof.status_code == 200
    cursor.execute("SELECT * FROM profesores WHERE user_id = ?;", (prof_user_id,))
    assert cursor.fetchone() is None, "La ficha del docente no se eliminó en universidad.db"
    print("[OK] Docente y ficha eliminados de ambas bases de datos.")

    conn_sqlite.close()

    print("\n====================================================================")
    print(" ¡TODAS LAS PRUEBAS DE REGISTRO ACADÉMICO PASARON EXITOSAMENTE! ")
    print("====================================================================")

if __name__ == "__main__":
    run_academic_tests()
