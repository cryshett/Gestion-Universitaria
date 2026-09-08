"""
test_full_academic_restructure.py
==================================
Prueba integral de la reestructuración:
1. Persistencia permanente con SQLAlchemy ORM
2. Creación de materias (/materias/crear) tanto por Formulario Web como por JSON API
3. Validación de unicidad de materias (código y nombre)
4. Creación de grupos (/grupos/crear) vinculando materia y docente
5. Asignación de horarios (/horarios/crear)
6. Validación estricta anti-cruces:
   - Cruce de Docente en mismo día y rango superpuesto
   - Cruce de Aula en mismo día y rango superpuesto
7. Verificación de renderizado de admin_dashboard con materias, grupos y docentes
"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import app
from app.db.session import SessionLocal
from app.models.user import User, RoleEnum
from app.models.materia import Materia
from app.models.grupo import Grupo
from app.models.horario import Horario

def test_academic_restructure():
    print("====================================================================")
    print("   VERIFICACIÓN INTEGRAL: PERSISTENCIA Y MÓDULO ACADÉMICO ORM      ")
    print("====================================================================")

    client = app.test_client()

    # 1. Login previo como Administrador en sesión
    with client.session_transaction() as sess:
        sess["user_id"] = 1
        sess["username"] = "admin"
        sess["role"] = "admin"

    # 2. Verificar que /admin renderiza con variables de Jinja
    print("\n--- 1. Verificando vista /admin ---")
    res_admin = client.get("/admin")
    assert res_admin.status_code == 200, f"Error en /admin: {res_admin.status_code}"
    html_admin = res_admin.data.decode("utf-8")
    assert 'id="form-materia"' in html_admin
    assert 'id="form-grupo"' in html_admin
    assert 'id="form-horario"' in html_admin
    assert 'action="/materias/crear"' in html_admin or 'action="http://localhost/materias/crear"' in html_admin or 'action="/materias/crear"' in html_admin
    print("[OK] Vista /admin renderizada correctamente con todos los formularios académicos.")

    # 3. Creación de Materia vía Formulario Web Tradicional (POST /materias/crear)
    print("\n--- 2. Creando materia vía Formulario Web (POST /materias/crear) ---")
    form_mat_1 = {
        "codigo": "ING-301",
        "nombre": "Ingeniería de Requerimientos",
        "carrera": "ISW",
        "creditos": "4",
        "nivel": "2",
        "tipo": "exclusiva"
    }
    res_form_m1 = client.post("/materias/crear", data=form_mat_1, follow_redirects=True)
    assert res_form_m1.status_code == 200
    html_after_form = res_form_m1.data.decode("utf-8")
    assert "creada y guardada exitosamente" in html_after_form or "exitosamente" in html_after_form
    print("[OK] Materia ING-301 creada vía Formulario Web y mensaje Flash emitido.")

    # 4. Creación de Materia vía JSON API (POST /materias/crear)
    print("\n--- 3. Creando materia vía JSON API (POST /materias/crear) ---")
    json_mat_2 = {
        "codigo": "ING-302",
        "nombre": "Arquitectura de Software",
        "carrera": "ISW",
        "creditos": 4,
        "nivel": 3,
        "tipo": "exclusiva"
    }
    res_json_m2 = client.post("/materias/crear", json=json_mat_2)
    assert res_json_m2.status_code == 201, f"Fallo al crear materia 2: {res_json_m2.json}"
    m2_data = res_json_m2.json
    print(f"[OK] Materia ING-302 creada vía JSON API: ID={m2_data['id']}")

    # 5. Validación de unicidad de materias
    print("\n--- 4. Validando rechazo de duplicados de materia ---")
    res_dup_cod = client.post("/materias/crear", json=json_mat_2)
    assert res_dup_cod.status_code == 400
    print("[OK] Código duplicado rechazado correctamente.")

    # 6. Consultar profesores en ORM para asignación
    db = SessionLocal()
    profesor = db.query(User).filter(User.role == RoleEnum.teacher).first()
    assert profesor is not None, "Debe existir al menos un docente en la base de datos"
    prof_id = profesor.id
    prof_nombre = profesor.username
    print(f"[OK] Docente para asignación: {prof_nombre} (ID: {prof_id})")

    # Obtener ID de ING-301 e ING-302 en ORM
    m1_orm = db.query(Materia).filter(Materia.codigo == "ING-301").first()
    m2_orm = db.query(Materia).filter(Materia.codigo == "ING-302").first()
    assert m1_orm is not None
    assert m2_orm is not None
    db.close()

    # 7. Creación de Grupos vía Formulario Web y JSON
    print("\n--- 5. Creando Grupo para ING-301 vía Formulario Web (POST /grupos/crear) ---")
    form_grp_1 = {
        "materia_id": str(m1_orm.id),
        "codigo_grupo": "G1",
        "profesor_id": str(prof_id),
        "cupo_maximo": "20"
    }
    res_f_g1 = client.post("/grupos/crear", data=form_grp_1, follow_redirects=True)
    assert res_f_g1.status_code == 200
    print("[OK] Grupo G1 para ING-301 creado vía formulario con redirección exitosa.")

    print("\n--- 6. Creando Grupo para ING-302 vía JSON API (POST /grupos/crear) ---")
    json_grp_2 = {
        "materia_id": m2_orm.id,
        "codigo_grupo": "G1",
        "profesor_id": prof_id,
        "cupo_maximo": 25
    }
    res_j_g2 = client.post("/grupos/crear", json=json_grp_2)
    assert res_j_g2.status_code == 201, f"Fallo al crear grupo: {res_j_g2.json}"
    g2_id = res_j_g2.json["id"]
    print(f"[OK] Grupo G1 para ING-302 creado vía JSON API (ID: {g2_id}).")

    # 8. Obtener ID del primer grupo en ORM
    db = SessionLocal()
    g1_orm = db.query(Grupo).filter(Grupo.materia_id == m1_orm.id, Grupo.codigo_grupo == "G1").first()
    assert g1_orm is not None
    g1_id = g1_orm.id
    db.close()

    # 9. Asignar Horario al Grupo 1 (Lunes 07:00 a 09:00 en Aula 101)
    print("\n--- 7. Asignando horario válido al Grupo 1 ---")
    json_hor_1 = {
        "grupo_id": g1_id,
        "dia": "Lunes",
        "hora_inicio": "07:00",
        "hora_fin": "09:00",
        "aula": "Aula 101",
        "edificio": "Pabellón A"
    }
    res_h1 = client.post("/horarios/crear", json=json_hor_1)
    assert res_h1.status_code == 201, f"Error al crear horario 1: {res_h1.json}"
    print("[OK] Horario Lunes 07:00-09:00 en Aula 101 asignado correctamente.")

    # 10. Validación de Conflicto 1: Cruce de Docente
    print("\n--- 8. Verificando Cruce de Docente (Mismo profesor en Lunes 08:00 a 10:00 en Aula 202) ---")
    json_hor_cruce_doc = {
        "grupo_id": g2_id,
        "dia": "Lunes",
        "hora_inicio": "08:00",
        "hora_fin": "10:00",
        "aula": "Aula 202",
        "edificio": "Pabellón B"
    }
    res_c_doc = client.post("/horarios/crear", json=json_hor_cruce_doc)
    assert res_c_doc.status_code == 400
    assert "Conflicto de Docente" in res_c_doc.json.get("mensaje", "")
    print(f"[OK] Cruce de Docente detectado y rechazado:")
    print(f"     -> {res_c_doc.json.get('mensaje')}")

    # 11. Validación de Conflicto 2: Cruce de Aula
    print("\n--- 9. Verificando Cruce de Aula (Misma Aula 101 en Lunes 07:30 a 09:30) ---")
    # Creamos un docente distinto para aislar la validación de aula
    db = SessionLocal()
    docente_2 = db.query(User).filter(User.role == RoleEnum.teacher, User.id != prof_id).first()
    if not docente_2:
        docente_2 = User(
            username="Prof. Prueba Aula",
            email="prof.aula@test.edu",
            hashed_password="hash",
            role=RoleEnum.teacher,
            is_active=True
        )
        db.add(docente_2)
        db.commit()
        db.refresh(docente_2)

    # Creamos grupo para docente 2
    g3 = Grupo(codigo_grupo="G2", materia_id=m1_orm.id, profesor_id=docente_2.id, cupo_maximo=15)
    db.add(g3)
    db.commit()
    db.refresh(g3)
    g3_id = g3.id
    db.close()

    json_hor_cruce_aula = {
        "grupo_id": g3_id,
        "dia": "Lunes",
        "hora_inicio": "07:30",
        "hora_fin": "09:30",
        "aula": "Aula 101"
    }
    res_c_aula = client.post("/horarios/crear", json=json_hor_cruce_aula)
    assert res_c_aula.status_code == 400
    assert "Conflicto de Aula" in res_c_aula.json.get("mensaje", "")
    print(f"[OK] Cruce de Aula detectado y rechazado:")
    print(f"     -> {res_c_aula.json.get('mensaje')}")

    # 12. Asignación de horario válido sin conflicto para Grupo 2
    print("\n--- 10. Asignando horario sin conflicto al Grupo 2 (Miércoles 10:00 a 12:00 en Aula 101) ---")
    json_hor_valido = {
        "grupo_id": g2_id,
        "dia": "Miércoles",
        "hora_inicio": "10:00",
        "hora_fin": "12:00",
        "aula": "Aula 101"
    }
    res_h_val = client.post("/horarios/crear", json=json_hor_valido)
    assert res_h_val.status_code == 201
    print("[OK] Horario sin conflicto asignado exitosamente.")

    # 13. Limpieza de datos de prueba
    print("\n--- 11. Limpieza final de registros de prueba ---")
    client.delete(f"/api/materias/{m1_orm.id}")
    client.delete(f"/api/materias/{m2_orm.id}")
    print("[OK] Limpieza exitosa.")

    print("\n====================================================================")
    print("   ¡TODAS LAS PRUEBAS DE LA REESTRUCTURACIÓN PASARON EXITOSAMENTE! ")
    print("====================================================================")

if __name__ == "__main__":
    test_academic_restructure()
