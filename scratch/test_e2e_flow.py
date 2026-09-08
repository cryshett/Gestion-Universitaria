import json
import urllib.request
import urllib.parse
import http.cookiejar

BASE_URL = "http://127.0.0.1:5000"

def test_e2e():
    cj = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

    def req(method, path, data=None):
        url = f"{BASE_URL}{path}"
        headers = {"Content-Type": "application/json"}
        body = json.dumps(data).encode("utf-8") if data is not None else None
        r = urllib.request.Request(url, data=body, headers=headers, method=method)
        try:
            with opener.open(r) as resp:
                status = resp.status
                content = resp.read().decode("utf-8")
                try:
                    return status, json.loads(content)
                except Exception:
                    return status, content
        except urllib.error.HTTPError as err:
            err_content = err.read().decode("utf-8")
            try:
                return err.code, json.loads(err_content)
            except Exception:
                return err.code, err_content

    print("--- 1. Probando acceso y login administrativo ---")
    st, res_login = req("POST", "/api/login", {
        "usuario": "admin",
        "clave": "Contraseña123"
    })
    assert st == 200, f"Error en login: {res_login}"
    print("[OK] Login exitoso como Administrador.")

    print("--- 2. Verificando vista admin renderizada ---")
    st, html = req("GET", "/admin")
    assert st == 200, f"Error al cargar /admin: {st}"
    assert 'id="badge-engine-status"' in html
    assert 'id="modal-materia"' in html
    assert 'id="modal-grupo"' in html
    assert 'id="modal-horario"' in html
    assert 'id="alerta-conflicto-horario"' in html
    assert 'id="btn-nueva-materia"' in html
    assert 'id="btn-nuevo-grupo"' in html
    assert 'id="btn-nuevo-horario"' in html
    print("[OK] Vista admin contiene todos los modales, botones y badges de control.")

    print("--- 3. Verificando API de Estado del Motor de Base de Datos ---")
    st, data_estado = req("GET", "/api/sistema/estado")
    assert st == 200
    print(f"[OK] Estado de base de datos reportado: {data_estado['motor']} (is_postgres={data_estado['is_postgres']})")

    # Limpiar posibles restos de ejecuciones previas
    st, mats = req("GET", "/api/materias")
    for m in mats:
        if m["codigo"] == "E2E-101":
            req("DELETE", f"/api/materias/{m['id']}")

    print("--- 4. Flujo CRUD completo de Materia ---")
    # Crear
    st, res_materia = req("POST", "/api/materias", {
        "codigo": "E2E-101",
        "nombre": "Arquitectura Hexagonal",
        "carrera_id": "ISW",
        "creditos": 4,
        "nivel": 3,
        "tipo": "exclusiva"
    })
    assert st == 201, f"Error al crear materia: {res_materia}"
    mat_id = res_materia["id"]
    print(f"[OK] Materia creada: {mat_id}")

    # Editar
    st, res_edit_mat = req("PUT", f"/api/materias/{mat_id}", {
        "codigo": "E2E-101",
        "nombre": "Arquitectura Hexagonal y Microservicios",
        "carrera_id": "ISW",
        "creditos": 5,
        "nivel": 3,
        "tipo": "exclusiva"
    })
    assert st == 200
    print("[OK] Materia editada con éxito.")

    print("--- 5. Flujo de Grupo Académico ---")
    st, profs = req("GET", "/api/profesores")
    prof_id = profs[0]["id"] if profs else None

    st, res_grupo = req("POST", "/api/grupos", {
        "asignatura_id": mat_id,
        "nombre": "G1",
        "profesor_id": prof_id,
        "cupo_maximo": 20
    })
    assert st == 201, f"Error al crear grupo: {res_grupo}"
    grupo_id = res_grupo["id"]
    print(f"[OK] Grupo creado: {grupo_id} asignado a docente {prof_id}")

    print("--- 6. Flujo de Horario y Detección de Conflictos ---")
    # Horario 1 (Válido)
    st, res_h1 = req("POST", "/api/horarios", {
        "grupo_id": grupo_id,
        "dia_semana": "Miércoles",
        "hora_inicio": "14:00",
        "hora_fin": "16:00",
        "aula": "Lab Software 2",
        "edificio": "Edificio Tecnológico"
    })
    assert st == 201, f"Error al asignar horario: {res_h1}"
    h1_id = res_h1["id"]
    print(f"[OK] Horario asignado: Miércoles 14:00-16:00 en Lab Software 2 (ID={h1_id})")

    # Conflicto de Aula: intentar asignar misma aula a misma hora
    st, res_conflicto = req("POST", "/api/horarios", {
        "grupo_id": grupo_id,
        "dia_semana": "Miércoles",
        "hora_inicio": "15:00",
        "hora_fin": "17:00",
        "aula": "Lab Software 2",
        "edificio": "Edificio Tecnológico"
    })
    assert st == 400
    print(f"[OK] Conflicto de aula detectado correctamente (400): {res_conflicto['mensaje']}")

    # Eliminar horario
    st, res_del_h = req("DELETE", f"/api/horarios/{h1_id}")
    assert st == 200
    print("[OK] Horario eliminado correctamente.")

    # Eliminar grupo
    st, res_del_grp = req("DELETE", f"/api/grupos/{grupo_id}")
    assert st == 200
    print("[OK] Grupo eliminado correctamente.")

    # Eliminar materia
    st, res_del_mat = req("DELETE", f"/api/materias/{mat_id}")
    assert st == 200
    print("[OK] Materia eliminada correctamente.")

    print("\n============================================================")
    print("   ¡FLUJO END-TO-END VERIFICADO EXITOSAMENTE AL 100%!       ")
    print("============================================================")

if __name__ == "__main__":
    test_e2e()
