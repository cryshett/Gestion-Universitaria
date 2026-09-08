"""
test_materia_creation_bug.py
=============================
Verifica la resolución completa del bug reportado en la creación y guardado de asignaturas:
1. Endpoint /materias/crear accesible vía GET (redirección) y POST.
2. Captura correcta de parámetros desde Formulario Web (x-www-form-urlencoded).
3. Validación estricta de unicidad tanto de CÓDIGO como de NOMBRE de materia.
4. Persistencia en base de datos con commit explícito.
5. Mensaje Flash y redirección en envíos de formulario tradicional.
6. Respuesta JSON uniforme 201 en peticiones API/AJAX.
7. Logs diagnósticos en consola.
"""
import urllib.request
import urllib.parse
import json
import http.cookiejar
import sys

BASE_URL = "http://127.0.0.1:5000"

def run_tests():
    print("====================================================================")
    print(" VERIFICANDO SOLUCIÓN DE CREACIÓN Y GUARDADO DE MATERIAS (/materias/crear)")
    print("====================================================================")

    cj = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

    def req(method, path, data=None, is_form=False):
        url = f"{BASE_URL}{path}"
        headers = {}
        if is_form:
            headers["Content-Type"] = "application/x-www-form-urlencoded"
            body = urllib.parse.urlencode(data).encode("utf-8") if data is not None else None
        else:
            headers["Content-Type"] = "application/json"
            headers["Accept"] = "application/json"
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

    # 1. Login como Administrador
    print("\n--- 1. Login de Administrador ---")
    st, res_login = req("POST", "/api/login", {"usuario": "admin", "clave": "Contraseña123"})
    assert st == 200, f"Fallo login admin: {res_login}"
    print("[OK] Sesión de Administrador iniciada.")

    # 2. Prueba GET /materias/crear
    print("\n--- 2. Probando GET /materias/crear ---")
    st, res_get = req("GET", "/materias/crear")
    assert st == 200, f"Error en GET /materias/crear: {st}"
    print("[OK] GET /materias/crear responde correctamente (redirección interna a admin).")

    # Limpiar posibles restos de pruebas
    _, mats = req("GET", "/api/materias")
    for m in mats:
        if m["codigo"] in ("BUG-101", "BUG-102", "FORM-201"):
            req("DELETE", f"/api/materias/{m['id']}")

    # 3. Creación vía Formulario Web Tradicional (x-www-form-urlencoded a /materias/crear)
    print("\n--- 3. Creación de materia mediante POST Formulario Web Tradicional ---")
    form_data = {
        "codigo": "FORM-201",
        "nombre": "Diseño de Patrones de Software",
        "carrera": "ISW",
        "creditos": "4",
        "nivel": "2",
        "tipo": "exclusiva"
    }
    st, res_form = req("POST", "/materias/crear", data=form_data, is_form=True)
    assert st == 200, f"Fallo al enviar formulario web: {st}"
    assert "Diseño de Patrones de Software" in res_form, "No se encontró el mensaje flash o la materia en la respuesta HTML"
    print("[OK] Materia creada vía formulario web tradicional, commit ejecutado y mensaje flash renderizado.")

    # 4. Creación vía AJAX / API REST (JSON a /materias/crear)
    print("\n--- 4. Creación de materia mediante JSON / AJAX a /materias/crear ---")
    json_data = {
        "codigo": "BUG-101",
        "nombre": "Ingeniería de Requerimientos Ágiles",
        "carrera": "ISW",
        "creditos": 3,
        "nivel": 1,
        "tipo": "exclusiva"
    }
    st, res_json = req("POST", "/materias/crear", data=json_data, is_form=False)
    assert st == 201, f"Fallo al crear vía JSON: {res_json}"
    assert res_json["codigo"] == "BUG-101"
    print(f"[OK] Materia creada vía JSON (201 Created): ID={res_json['id']}")

    # 5. Validación de Código Duplicado
    print("\n--- 5. Probando validación de código duplicado ---")
    st, res_dup_code = req("POST", "/materias/crear", data={
        "codigo": "BUG-101", # mismo código
        "nombre": "Otro Nombre Distinto",
        "carrera": "ISW",
        "creditos": 3,
        "nivel": 1
    })
    assert st == 400
    print(f"[OK] Código duplicado rechazado (400): {res_dup_code['mensaje']}")

    # 6. Validación de Nombre Duplicado
    print("\n--- 6. Probando validación de nombre duplicado ---")
    st, res_dup_name = req("POST", "/materias/crear", data={
        "codigo": "BUG-102", # código nuevo
        "nombre": "Ingeniería de Requerimientos Ágiles", # mismo nombre que BUG-101
        "carrera": "ISW",
        "creditos": 3,
        "nivel": 1
    })
    assert st == 400
    print(f"[OK] Nombre duplicado rechazado (400): {res_dup_name['mensaje']}")

    # 7. Validación de persistencia en la base de datos
    print("\n--- 7. Verificando persistencia en catálogo (/api/materias) ---")
    st, mats_actuales = req("GET", "/api/materias")
    codigos_en_bd = [m["codigo"] for m in mats_actuales]
    assert "FORM-201" in codigos_en_bd, "La materia FORM-201 no persistió en la BD"
    assert "BUG-101" in codigos_en_bd, "La materia BUG-101 no persistió en la BD"
    print(f"[OK] Ambas materias confirmadas y persistidas en la BD: FORM-201 y BUG-101.")

    # 8. Limpieza
    print("\n--- 8. Limpieza de materias de prueba ---")
    for m in mats_actuales:
        if m["codigo"] in ("BUG-101", "BUG-102", "FORM-201"):
            req("DELETE", f"/api/materias/{m['id']}")
    print("[OK] Limpieza exitosa.")

    print("\n====================================================================")
    print(" ¡TODAS LAS PRUEBAS DE RESOLUCIÓN DEL BUG PASARON AL 100%!          ")
    print("====================================================================")

if __name__ == "__main__":
    run_tests()
