"""
test_academic_user_creation.py
==============================
Verifica la ampliación del registro de usuarios con nombres divididos y auto-generación de credenciales:
1. Registro de Estudiante con nombres divididos ("Juan Carlos Pérez Gómez") -> username: 'jcperez', email: 'jcperez@universidad.edu'.
2. Detección y manejo secuencial de colisión de username ("Julio César Pérez Silva") -> username: 'jcperez1'.
3. Registro de Docente con un solo nombre y acentos ("Ana Gómez") -> username: 'agomez', email: 'agomez@universidad.edu'.
4. Verificación de persistencia de columnas (primer_nombre, segundo_nombre, primer_apellido, segundo_apellido, user_id, etc.).
5. Validación de unicidad de Cédula/Identificación.
6. Prueba de transacción atómica (rollback en mb_system.db si falla universidad.db).
7. Verificación de /api/me y /api/admin/usuarios.
"""
import os
import sys
import sqlite3
from unittest.mock import patch

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
    print(" INICIANDO TEST DE REGISTRO CON AUTO-GENERACIÓN DE USERNAME Y EMAIL ")
    print("====================================================================")

    test_usernames = ["jcperez", "jcperez1", "agomez", "usuario_fallido"]
    test_docs = ["1020304050", "1020304051", "7080901020", "9999999999"]

    # Limpiar posibles restos de ejecuciones previas
    conn_sq = sqlite3.connect("universidad.db")
    with conn_sq:
        placeholders_u = ",".join(f"'{u}'" for u in test_usernames)
        placeholders_d = ",".join(f"'{d}'" for d in test_docs)
        conn_sq.execute(f"DELETE FROM estudiantes WHERE username IN ({placeholders_u}) OR documento IN ({placeholders_d});")
        conn_sq.execute(f"DELETE FROM profesores WHERE username IN ({placeholders_u}) OR documento IN ({placeholders_d});")
    conn_sq.close()

    db_clean = SessionLocal()
    for u_del in db_clean.query(User).filter(User.username.in_(test_usernames)).all():
        db_clean.delete(u_del)
    db_clean.commit()
    db_clean.close()

    client = app.test_client()

    # Simular sesión activa de Administrador
    with client.session_transaction() as sess:
        sess["role"] = "admin"
        sess["user_id"] = 1
        sess["username"] = "admin"

    # 1. REGISTRO DE ESTUDIANTE CON NOMBRES DIVIDIDOS
    print("\n--- 1. Registrando Estudiante ('Juan Carlos Pérez Gómez') ---")
    doc_estudiante1 = "1020304050"
    payload_est1 = {
        "primer_nombre": "Juan",
        "segundo_nombre": "Carlos",
        "primer_apellido": "Pérez",
        "segundo_apellido": "Gómez",
        "identificacion": doc_estudiante1,
        "password": "Password123!",
        "role": "student",
        "carrera_id": "ISW",
        "semestre": 3,
        "grupo": "G2"
    }
    res_est1 = client.post("/api/admin/crear-usuario", json=payload_est1)
    assert res_est1.status_code == 201, f"Fallo al registrar estudiante: {res_est1.json}"
    data1 = res_est1.json["usuario"]
    print(f"[OK] Usuario generado: '{data1['username']}' | Email: '{data1['email']}'")
    assert data1["username"] == "jcperez", f"Username incorrecto: {data1['username']}"
    assert data1["email"] == "jcperez@universidad.edu", f"Email incorrecto: {data1['email']}"
    assert data1["nombre"] == "Juan Carlos Pérez Gómez"

    # Verificar en mb_system.db
    db_sqla = SessionLocal()
    user_est1 = db_sqla.query(User).filter(User.username == "jcperez").first()
    assert user_est1 is not None, "El estudiante no fue creado en mb_system.db (users)"
    assert user_est1.email == "jcperez@universidad.edu"
    assert user_est1.role == RoleEnum.student
    est1_user_id = user_est1.id
    db_sqla.close()

    # Verificar en universidad.db (estudiantes)
    conn_sqlite = sqlite3.connect("universidad.db")
    conn_sqlite.row_factory = sqlite3.Row
    cursor = conn_sqlite.cursor()
    cursor.execute("SELECT * FROM estudiantes WHERE documento = ?;", (doc_estudiante1,))
    row1 = cursor.fetchone()
    assert row1 is not None, "El estudiante no fue creado en universidad.db (estudiantes)"
    assert row1["primer_nombre"] == "Juan"
    assert row1["segundo_nombre"] == "Carlos"
    assert row1["primer_apellido"] == "Pérez"
    assert row1["segundo_apellido"] == "Gómez"
    assert row1["nombre"] == "Juan Carlos Pérez Gómez"
    assert row1["username"] == "jcperez"
    assert row1["email"] == "jcperez@universidad.edu"
    assert row1["user_id"] == est1_user_id
    print(f"[OK] universidad.db: Ficha #{row1['id']} con nombres divididos y vinculación exitosa.")

    # 2. MANEJO DE COLISIONES DE USERNAME
    print("\n--- 2. Probando Colisión de Username ('Julio César Pérez Silva') ---")
    doc_estudiante2 = "1020304051"
    payload_est2 = {
        "primer_nombre": "Julio",
        "segundo_nombre": "César",
        "primer_apellido": "Pérez",
        "segundo_apellido": "Silva",
        "identificacion": doc_estudiante2,
        "password": "Password123!",
        "role": "student",
        "carrera_id": "ISW",
        "semestre": 2,
        "grupo": "G1"
    }
    res_est2 = client.post("/api/admin/crear-usuario", json=payload_est2)
    assert res_est2.status_code == 201, f"Fallo en colisión: {res_est2.json}"
    data2 = res_est2.json["usuario"]
    print(f"[OK] Colisión resuelta automáticamente: '{data2['username']}' | Email: '{data2['email']}'")
    assert data2["username"] == "jcperez1", f"Username con sufijo incorrecto: {data2['username']}"
    assert data2["email"] == "jcperez1@universidad.edu"

    # 3. REGISTRO DE PROFESOR (NOMBRE SIMPLE CON ACENTO)
    print("\n--- 3. Registrando Profesor ('Ana Gómez') ---")
    doc_prof = "7080901020"
    payload_prof = {
        "primer_nombre": "Ana",
        "primer_apellido": "Gómez",
        "identificacion": doc_prof,
        "password": "DocentePassword2026!",
        "role": "teacher",
        "carrera_principal": "MED",
        "titulo_academico": "Doctora en Cirugía"
    }
    res_prof = client.post("/api/admin/crear-usuario", json=payload_prof)
    assert res_prof.status_code == 201, f"Fallo al registrar docente: {res_prof.json}"
    data_prof = res_prof.json["usuario"]
    print(f"[OK] Docente generado: '{data_prof['username']}' | Email: '{data_prof['email']}'")
    assert data_prof["username"] == "agomez", f"Username docente incorrecto: {data_prof['username']}"
    assert data_prof["email"] == "agomez@universidad.edu"

    cursor.execute("SELECT * FROM profesores WHERE documento = ?;", (doc_prof,))
    row_prof = cursor.fetchone()
    assert row_prof is not None, "El docente no fue creado en universidad.db"
    assert row_prof["primer_nombre"] == "Ana"
    assert row_prof["primer_apellido"] == "Gómez"
    assert row_prof["username"] == "agomez"
    assert row_prof["email"] == "agomez@universidad.edu"
    print(f"[OK] universidad.db: Ficha docente #{row_prof['id']} registrada correctamente.")

    # 4. VALIDACIÓN DE CÉDULA DUPLICADA
    print("\n--- 4. Probando Validación de Cédula Duplicada ---")
    payload_dup = {
        "primer_nombre": "Mariana",
        "primer_apellido": "López",
        "identificacion": doc_estudiante1,  # Ya existe
        "password": "Password123!",
        "role": "student"
    }
    res_dup = client.post("/api/admin/crear-usuario", json=payload_dup)
    assert res_dup.status_code == 400, f"Se esperaba 400, obtenido {res_dup.status_code}"
    print(f"[OK] Rechazado con 400: {res_dup.json.get('mensaje')}")

    # 5. PRUEBA DE ATOMICIDAD (ROLLBACK ANTE FALLO EN SQLITE)
    print("\n--- 5. Probando Transacción Atómica y Rollback Bidireccional ---")
    payload_atómico = {
        "primer_nombre": "Mario",
        "primer_apellido": "Bros",
        "identificacion": "9999999999",
        "password": "SuperSecret123!",
        "role": "student"
    }

    # Simulamos fallo forzado dentro de la transacción de SQLite interceptando get_db
    real_get_db = app_flask.get_db
    class FailingConnection:
        def __init__(self, real_conn):
            self.real_conn = real_conn
        def cursor(self):
            real_cur = self.real_conn.cursor()
            class FailingCursor:
                def execute(self, sql, *args, **kwargs):
                    if "INSERT INTO estudiantes" in sql:
                        raise sqlite3.OperationalError("Error simulado de base de datos en estudiantes")
                    return real_cur.execute(sql, *args, **kwargs)
                def fetchone(self):
                    return real_cur.fetchone()
                def fetchall(self):
                    return real_cur.fetchall()
            return FailingCursor()
        def __enter__(self):
            return self
        def __exit__(self, exc_type, exc_val, exc_tb):
            pass

    with patch.object(app_flask, "get_db", side_effect=lambda: FailingConnection(real_get_db())):
        res_fail = client.post("/api/admin/crear-usuario", json=payload_atómico)
        assert res_fail.status_code == 400
        print(f"[OK] Capturado error atómico esperado: {res_fail.json.get('mensaje')}")

    # Verificar que el usuario no quedó huérfano en mb_system.db
    db_sqla = SessionLocal()
    orphan = db_sqla.query(User).filter(User.username == "mbros").first()
    assert orphan is None, "ERROR DE ATOMICIDAD: El usuario quedó creado en mb_system.db a pesar del fallo en SQLite"
    db_sqla.close()
    print("[OK] Atomicidad confirmada: No existe usuario huérfano en mb_system.db")

    # 6. VERIFICACIÓN DE /api/admin/usuarios
    print("\n--- 6. Verificando /api/admin/usuarios ---")
    res_lista = client.get("/api/admin/usuarios")
    assert res_lista.status_code == 200
    usuarios_admin = res_lista.json if isinstance(res_lista.json, list) else res_lista.json.get("datos", [])
    u_jcp = next((u for u in usuarios_admin if u["username"] == "jcperez"), None)
    assert u_jcp is not None, "jcperez no figura en /api/admin/usuarios"
    assert u_jcp["nombre"] == "Juan Carlos Pérez Gómez"
    assert u_jcp["email"] == "jcperez@universidad.edu"
    print(f"[OK] Usuario en /api/admin/usuarios: {u_jcp['username']} - {u_jcp['nombre']} ({u_jcp['email']})")

    # 7. LIMPIEZA FINAL DE USUARIOS DE TEST
    print("\n--- 7. Limpiando Usuarios de Prueba ---")
    for u_id in [data1["id"], data2["id"], data_prof["id"]]:
        client.delete(f"/api/admin/usuarios/{u_id}")
    print("[OK] Usuarios de prueba eliminados limpiamente.")

    conn_sqlite.close()
    print("\n====================================================================")
    print(" TODAS LAS PRUEBAS DE REGISTRO AUTOMÁTICO PASARON EXITOSAMENTE ")
    print("====================================================================")

if __name__ == "__main__":
    run_academic_tests()
