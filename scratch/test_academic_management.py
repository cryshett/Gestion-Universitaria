"""
scratch/test_academic_management.py
====================================
Prueba automatizada integral del Módulo de Gestión Académica:
1. Estado del motor de base de datos (PostgreSQL/SQLite)
2. CRUD completo de Materias (Asignaturas)
3. Listado de Profesores disponibles
4. Creación y asignación de Grupos Académicos
5. Asignación de Horarios
6. Validación rigurosa de conflictos de horario:
   - Cruce de Docente (mismo profesor en horario superpuesto)
   - Cruce de Aula (misma aula física en horario superpuesto)
7. Limpieza y desasignación en cascada
"""

import os
import sys
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import app
from app.db.connection import get_raw_connection

def test_academic_management():
    print("====================================================================")
    print("   INICIANDO PRUEBAS DEL MÓDULO DE MATERIAS, GRUPOS Y HORARIOS     ")
    print("====================================================================")

    client = app.test_client()

    # 1. Estado del motor de base de datos
    print("\n--- 1. Verificando estado del motor de base de datos ---")
    res_status = client.get("/api/sistema/estado")
    assert res_status.status_code == 200, f"Error en /api/sistema/estado: {res_status.json}"
    status_data = res_status.json
    print(f"[OK] Motor detectado: {status_data['motor']} (is_postgres={status_data['is_postgres']})")

    # 2. Asegurar que existe al menos un profesor para las pruebas
    print("\n--- 2. Verificando profesores disponibles para asignación ---")
    db = get_raw_connection()
    with db:
        db.execute("""
            INSERT INTO profesores (id, documento, nombre, email, carrera_principal, estado)
            VALUES ('DOC-TEST-01', '99887766', 'Prof. Alan Turing', 'alan.turing@universidad.edu', 'ISW', 'Activo')
            ON CONFLICT (id) DO NOTHING;
        """ if db.is_postgres else """
            INSERT OR IGNORE INTO profesores (id, documento, nombre, email, carrera_principal, estado)
            VALUES ('DOC-TEST-01', '99887766', 'Prof. Alan Turing', 'alan.turing@universidad.edu', 'ISW', 'Activo');
        """)

        # Segundo profesor para pruebas cruzadas
        db.execute("""
            INSERT INTO profesores (id, documento, nombre, email, carrera_principal, estado)
            VALUES ('DOC-TEST-02', '99887767', 'Prof. Ada Lovelace', 'ada.lovelace@universidad.edu', 'ISW', 'Activo')
            ON CONFLICT (id) DO NOTHING;
        """ if db.is_postgres else """
            INSERT OR IGNORE INTO profesores (id, documento, nombre, email, carrera_principal, estado)
            VALUES ('DOC-TEST-02', '99887767', 'Prof. Ada Lovelace', 'ada.lovelace@universidad.edu', 'ISW', 'Activo');
        """)
    db.close()

    res_profs = client.get("/api/profesores")
    assert res_profs.status_code == 200, "Fallo al listar profesores"
    profs = res_profs.json
    assert any(p["id"] == "DOC-TEST-01" for p in profs), "Profesor Alan Turing no encontrado"
    print(f"[OK] {len(profs)} profesores listados correctamente.")

    # 3. Crear Materia 1 y Materia 2
    print("\n--- 3. Creando materias de prueba ---")
    materia_1_payload = {
        "codigo": "TEST-101",
        "nombre": "Algoritmos Avanzados",
        "creditos": 4,
        "carrera_id": "ISW",
        "nivel": 2,
        "tipo": "exclusiva"
    }
    res_m1 = client.post("/api/materias", json=materia_1_payload)
    assert res_m1.status_code == 201, f"Fallo al crear materia 1: {res_m1.json}"
    m1_data = res_m1.json
    print(f"[OK] Materia creada: {m1_data['nombre']} ({m1_data['codigo']}) -> ID: {m1_data['id']}")

    materia_2_payload = {
        "codigo": "TEST-102",
        "nombre": "Bases de Datos Distribuidas",
        "creditos": 4,
        "carrera_id": "ISW",
        "nivel": 2,
        "tipo": "exclusiva"
    }
    res_m2 = client.post("/api/materias", json=materia_2_payload)
    assert res_m2.status_code == 201, f"Fallo al crear materia 2: {res_m2.json}"
    m2_data = res_m2.json
    print(f"[OK] Materia creada: {m2_data['nombre']} ({m2_data['codigo']}) -> ID: {m2_data['id']}")

    # 4. Probar rechazo de código duplicado
    res_dup = client.post("/api/materias", json=materia_1_payload)
    assert res_dup.status_code == 400, "Debería rechazar código duplicado"
    print("[OK] Código duplicado rechazado correctamente.")

    # 5. Crear Grupos
    print("\n--- 4. Creando grupos académicos y asignando docentes ---")
    grupo_1_payload = {
        "asignatura_id": m1_data["id"],
        "nombre": "G1",
        "profesor_id": "DOC-TEST-01",
        "cupo_maximo": 15
    }
    res_g1 = client.post("/api/grupos", json=grupo_1_payload)
    assert res_g1.status_code == 201, f"Fallo al crear grupo 1: {res_g1.json}"
    g1_id = res_g1.json["id"]
    print(f"[OK] Grupo 1 creado: ID={g1_id}, Profesor='{res_g1.json['profesor_nombre']}'")

    grupo_2_payload = {
        "asignatura_id": m2_data["id"],
        "nombre": "G1",
        "profesor_id": "DOC-TEST-01",  # Mismo profesor que G1 para probar colisión
        "cupo_maximo": 15
    }
    res_g2 = client.post("/api/grupos", json=grupo_2_payload)
    assert res_g2.status_code == 201, f"Fallo al crear grupo 2: {res_g2.json}"
    g2_id = res_g2.json["id"]
    print(f"[OK] Grupo 2 creado: ID={g2_id}, Mismo Profesor='Alan Turing'")

    grupo_3_payload = {
        "asignatura_id": m2_data["id"],
        "nombre": "G2",
        "profesor_id": "DOC-TEST-02",  # Profesor Ada Lovelace
        "cupo_maximo": 15
    }
    res_g3 = client.post("/api/grupos", json=grupo_3_payload)
    assert res_g3.status_code == 201, f"Fallo al crear grupo 3: {res_g3.json}"
    g3_id = res_g3.json["id"]
    print(f"[OK] Grupo 3 creado: ID={g3_id}, Profesora='Ada Lovelace'")

    # 6. Asignar Horario al Grupo 1 (Lunes 07:00 a 09:00 en Aula Lab-101)
    print("\n--- 5. Asignando primer horario válido ---")
    horario_1_payload = {
        "grupo_id": g1_id,
        "dia_semana": "Lunes",
        "hora_inicio": "07:00",
        "hora_fin": "09:00",
        "aula": "Lab 101"
    }
    res_h1 = client.post("/api/horarios", json=horario_1_payload)
    assert res_h1.status_code == 201, f"Fallo al asignar horario 1: {res_h1.json}"
    print(f"[OK] Horario 1 registrado: Lunes 07:00-09:00 en Lab 101 para Grupo 1.")

    # 7. Validación de conflicto: DOCENTE SOLAPADO
    print("\n--- 6. Probando Validación de Conflicto: CRUCE DE DOCENTE ---")
    # Intentamos asignar Grupo 2 (con Alan Turing) el Lunes de 08:00 a 10:00 (solapa con 07:00-09:00) en Aula 202
    horario_conflicto_doc = {
        "grupo_id": g2_id,
        "dia_semana": "Lunes",
        "hora_inicio": "08:00",
        "hora_fin": "10:00",
        "aula": "Aula 202"
    }
    res_c_doc = client.post("/api/horarios", json=horario_conflicto_doc)
    assert res_c_doc.status_code == 400, f"Debería rechazar por cruce de docente, recibido: {res_c_doc.status_code}"
    print(f"[OK] Cruce de Docente detectado y rechazado correctamente con 400:")
    print(f"     Mensaje: {res_c_doc.json.get('mensaje')}")
    assert "Conflicto de Docente" in res_c_doc.json.get("mensaje", ""), "Mensaje no indica conflicto de docente"

    # 8. Validación de conflicto: AULA SOLAPADA
    print("\n--- 7. Probando Validación de Conflicto: CRUCE DE AULA ---")
    # Intentamos asignar Grupo 3 (con Ada Lovelace) el Lunes de 07:30 a 09:30 en el mismo Lab 101
    horario_conflicto_aula = {
        "grupo_id": g3_id,
        "dia_semana": "Lunes",
        "hora_inicio": "07:30",
        "hora_fin": "09:30",
        "aula": "Lab 101"
    }
    res_c_aula = client.post("/api/horarios", json=horario_conflicto_aula)
    assert res_c_aula.status_code == 400, f"Debería rechazar por cruce de aula, recibido: {res_c_aula.status_code}"
    print(f"[OK] Cruce de Aula detectado y rechazado correctamente con 400:")
    print(f"     Mensaje: {res_c_aula.json.get('mensaje')}")
    assert "Conflicto de Aula" in res_c_aula.json.get("mensaje", ""), "Mensaje no indica conflicto de aula"

    # 9. Asignar Horario no conflictivo al Grupo 3 (Martes 09:00 a 11:00 en Lab 101)
    print("\n--- 8. Asignando horario sin conflicto al Grupo 3 ---")
    horario_valido_g3 = {
        "grupo_id": g3_id,
        "dia_semana": "Martes",
        "hora_inicio": "09:00",
        "hora_fin": "11:00",
        "aula": "Lab 101"
    }
    res_h3 = client.post("/api/horarios", json=horario_valido_g3)
    assert res_h3.status_code == 201, f"Fallo al asignar horario válido al grupo 3: {res_h3.json}"
    print("[OK] Horario para Grupo 3 asignado correctamente.")

    # 10. Consultar matriz de horarios completa
    print("\n--- 9. Consultando matriz general de horarios configurados ---")
    res_all_h = client.get("/api/horarios")
    assert res_all_h.status_code == 200, "Fallo al consultar horarios"
    horarios_list = res_all_h.json
    assert len(horarios_list) >= 2, f"Se esperaban al menos 2 horarios, se encontraron {len(horarios_list)}"
    print(f"[OK] Total de horarios recuperados: {len(horarios_list)}")
    for h in horarios_list:
        if h["grupo_id"] in (g1_id, g3_id):
            print(f"     - {h['dia_semana']} {h['hora_inicio']}-{h['hora_fin']} | {h['materia_nombre']} ({h['grupo_nombre']}) | {h['aula']} | Prof: {h['profesor_nombre']}")

    # 11. Limpieza de datos de prueba
    print("\n--- 10. Limpiando datos de prueba generados ---")
    client.delete(f"/api/materias/{m1_data['id']}")
    client.delete(f"/api/materias/{m2_data['id']}")
    db = get_raw_connection()
    with db:
        db.execute("DELETE FROM profesores WHERE id IN ('DOC-TEST-01', 'DOC-TEST-02');")
    db.close()
    print("[OK] Limpieza completada.")

    print("\n====================================================================")
    print("   ¡TODAS LAS PRUEBAS DE GESTIÓN ACADÉMICA PASARON EXITOSAMENTE!    ")
    print("====================================================================")

if __name__ == "__main__":
    test_academic_management()
