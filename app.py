"""
app.py
======
Servidor Web Flask y API RESTful Refactorizado con Buenas Prácticas de Desarrollo.

Patrones de Diseño y Buenas Prácticas Aplicados:
1. Gestión de Recursos con Flask `g`: Apertura y cierre automático de la BD por cada petición HTTP (sin memory leaks).
2. Manejo de Errores Centralizado: Respuestas JSON uniformes con códigos de estado HTTP adecuados (200, 201, 400, 404, 500).
3. Type Hints y Type Annotations: Firma clara de funciones para evitar errores de tipo.
4. Separación de Responsabilidades: Rutas limpias, validación de entrada e invocación modular.
"""

from flask import Flask, render_template, jsonify, request, g, Response, session, redirect, url_for
import sqlite3
import os
import uuid
from datetime import datetime, timedelta
from typing import Tuple, Dict, Any, List

# Importaciones de mb-system Auth & DB
from app.db.session import engine, SessionLocal
from app.db.base import Base
from app.models.user import User, RoleEnum
from app.models.token import RefreshToken
from app.models.login_history import LoginHistory
from app.core.security import hash_password, verify_password, create_access_token, create_refresh_token, decode_token
from app.core.config import settings

# Creación/Metadatos de tablas mb-system
Base.metadata.create_all(bind=engine)

def init_universidad_db():
    """Inicializa y asegura la estructura completa de tablas en universidad.db (SQLite)."""
    conn = sqlite3.connect("universidad.db")
    cursor = conn.cursor()
    cursor.executescript("""
        CREATE TABLE IF NOT EXISTS carreras (
            id VARCHAR(10) PRIMARY KEY,
            nombre VARCHAR(100) NOT NULL,
            codigo VARCHAR(20) UNIQUE NOT NULL,
            duracion_semestres INT NOT NULL,
            total_creditos INT NOT NULL,
            cupos_maximos INT NOT NULL DEFAULT 30,
            color VARCHAR(20) NOT NULL,
            descripcion TEXT NOT NULL,
            icono VARCHAR(50) NOT NULL
        );

        CREATE TABLE IF NOT EXISTS profesores (
            id VARCHAR(20) PRIMARY KEY,
            documento VARCHAR(20) UNIQUE NOT NULL,
            nombre VARCHAR(100) NOT NULL,
            email VARCHAR(100) UNIQUE NOT NULL,
            telefono VARCHAR(30) DEFAULT '+52 55 5555-0000',
            titulo_academico VARCHAR(100) DEFAULT 'Docente Titular',
            carrera_principal VARCHAR(10) NOT NULL,
            estado VARCHAR(20) NOT NULL DEFAULT 'Activo',
            username VARCHAR(50) DEFAULT '',
            user_id INT DEFAULT NULL
        );

        CREATE TABLE IF NOT EXISTS asignaturas (
            id VARCHAR(20) PRIMARY KEY,
            codigo VARCHAR(20) UNIQUE NOT NULL,
            nombre VARCHAR(150) NOT NULL,
            creditos INT NOT NULL,
            nivel INT NOT NULL CHECK (nivel IN (1, 2, 3)),
            tipo VARCHAR(20) NOT NULL CHECK (tipo IN ('exclusiva', 'compartida')),
            carrera_id VARCHAR(10) DEFAULT NULL,
            carreras_compartidas VARCHAR(100) DEFAULT NULL,
            docente VARCHAR(100) NOT NULL,
            horario VARCHAR(50) NOT NULL,
            grupo VARCHAR(10) NOT NULL DEFAULT 'G1',
            aula VARCHAR(50) NOT NULL DEFAULT 'Aula 101'
        );

        CREATE TABLE IF NOT EXISTS estudiantes (
            id VARCHAR(20) PRIMARY KEY,
            matricula VARCHAR(30) UNIQUE NOT NULL,
            documento VARCHAR(20) UNIQUE,
            nombre VARCHAR(100) NOT NULL,
            email VARCHAR(100) NOT NULL,
            telefono VARCHAR(30) DEFAULT '+52 55 5555-5555',
            carrera_id VARCHAR(10) NOT NULL,
            semestre INT NOT NULL CHECK (semestre BETWEEN 1 AND 10),
            grupo VARCHAR(10) NOT NULL DEFAULT 'G1',
            estado VARCHAR(20) NOT NULL CHECK (estado IN ('Activo', 'En Riesgo', 'Egresado', 'Suspendido')) DEFAULT 'Activo',
            estado_pago VARCHAR(20) NOT NULL DEFAULT 'Al día' CHECK (estado_pago IN ('Al día', 'Pendiente', 'Bloqueado')),
            promedio DOUBLE NOT NULL DEFAULT 0.0,
            foto_avatar VARCHAR(255) NOT NULL,
            username VARCHAR(50) DEFAULT '',
            user_id INT DEFAULT NULL
        );

        CREATE TABLE IF NOT EXISTS inscripciones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            estudiante_id VARCHAR(20) NOT NULL,
            asignatura_id VARCHAR(20) NOT NULL,
            nota DOUBLE NOT NULL CHECK (nota BETWEEN 0.0 AND 5.0),
            periodo VARCHAR(20) NOT NULL DEFAULT '2026-1',
            UNIQUE (estudiante_id, asignatura_id)
        );

        CREATE TABLE IF NOT EXISTS notificaciones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            estudiante_id VARCHAR(20) NOT NULL,
            titulo VARCHAR(150) NOT NULL,
            mensaje TEXT NOT NULL,
            tipo VARCHAR(20) NOT NULL DEFAULT 'pago' CHECK (tipo IN ('pago', 'academico', 'sistema')),
            fecha VARCHAR(30) NOT NULL,
            leido TINYINT(1) NOT NULL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS solicitudes_cambio_grupo (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            estudiante_id VARCHAR(20) NOT NULL,
            asignatura_id VARCHAR(20) NOT NULL,
            grupo_actual VARCHAR(10) NOT NULL,
            grupo_solicitado VARCHAR(10) NOT NULL,
            motivo TEXT NOT NULL,
            estado VARCHAR(20) NOT NULL DEFAULT 'PENDIENTE',
            fecha VARCHAR(30) NOT NULL,
            fecha_resolucion VARCHAR(30) DEFAULT NULL,
            respuesta_admin TEXT DEFAULT NULL
        );
    """)

    # Asegurar columnas necesarias en caso de tablas preexistentes
    def agregar_columna_si_falta(tabla, columna, definicion):
        cols = [c[1] for c in cursor.execute(f"PRAGMA table_info({tabla});").fetchall()]
        if columna not in cols:
            cursor.execute(f"ALTER TABLE {tabla} ADD COLUMN {columna} {definicion};")

    agregar_columna_si_falta("estudiantes", "documento", "VARCHAR(20) UNIQUE")
    agregar_columna_si_falta("estudiantes", "grupo", "VARCHAR(10) DEFAULT 'G1'")
    agregar_columna_si_falta("estudiantes", "username", "VARCHAR(50) DEFAULT ''")
    agregar_columna_si_falta("estudiantes", "user_id", "INT DEFAULT NULL")

    agregar_columna_si_falta("profesores", "username", "VARCHAR(50) DEFAULT ''")
    agregar_columna_si_falta("profesores", "user_id", "INT DEFAULT NULL")

    # Poblar carreras institucionales si la tabla está vacía
    cursor.execute("SELECT COUNT(*) FROM carreras;")
    if cursor.fetchone()[0] == 0:
        carreras_base = [
            ("ISW", "Ingeniería de Software", "ISW", 8, 160, 30, "#3b82f6", "Formación integral en desarrollo y arquitectura de software.", "code"),
            ("MED", "Medicina Humana", "MED", 10, 220, 30, "#10b981", "Excelencia médica, ciencias biológicas y salud comunitaria.", "stethoscope"),
            ("DER", "Derecho y Ciencias Políticas", "DER", 8, 150, 30, "#8b5cf6", "Ciencias jurídicas, derecho civil, penal y corporativo.", "scale")
        ]
        cursor.executemany("INSERT INTO carreras VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);", carreras_base)

    conn.commit()
    conn.close()

init_universidad_db()

def asegurar_admin_mbsystem():
    """Garantiza la existencia del usuario Administrador exclusivo de MBSystem (admin / admin@mbsystem.com)."""
    db = SessionLocal()
    try:
        existing_admin = db.query(User).filter(
            (User.username == "admin") | (User.email == "admin@mbsystem.com")
        ).first()
        if not existing_admin:
            admin = User(
                username="admin",
                email="admin@mbsystem.com",
                hashed_password=hash_password("Contraseña123"),
                role=RoleEnum.admin,
                is_active=True
            )
            db.add(admin)
            db.commit()
    finally:
        db.close()

asegurar_admin_mbsystem()

# =============================================================================
# EXPORTACIÓN GLOBAL DE LA INSTANCIA 'app' DE FLASK PARA GUNICORN / WSGI
# =============================================================================
app = Flask(__name__, template_folder="templates", static_folder="static")
app.secret_key = settings.SECRET_KEY

# Constantes del Dominio
NOTA_MINIMA_APROBATORIA: float = 3.5
ESCALA_MAXIMA_NOTA: float = 5.0

# =============================================================================
# GESTIÓN DE CONEXIÓN A BASE DE DATOS MEDIANTE FLASK 'g' CONTEXT
# =============================================================================
def get_db() -> sqlite3.Connection:
    """
    Obtiene la conexión a la base de datos SQLite para la petición HTTP actual.
    Si la conexión no existe aún en 'g', la crea y almacena.
    """
    if 'db' not in g:
        g.db = sqlite3.connect("universidad.db")
        g.db.row_factory = sqlite3.Row
    return g.db


def get_sqlalchemy_db():
    """Obtiene la sesión de SQLAlchemy (mb-system) para la petición actual."""
    if 'sqla_db' not in g:
        g.sqla_db = SessionLocal()
    return g.sqla_db


@app.teardown_appcontext
def close_db(exception: Exception = None) -> None:
    """
    Se ejecuta automáticamente al finalizar la petición HTTP.
    Garantiza el cierre seguro de las conexiones a base de datos.
    """
    db = g.pop('db', None)
    if db is not None:
        db.close()

    sqla_db = g.pop('sqla_db', None)
    if sqla_db is not None:
        sqla_db.close()


# =============================================================================
# FUNCIONES AUXILIARES DE ENTRADA / SALIDA Y RESPUESTA REST API
# =============================================================================
def obtener_datos_peticion() -> Dict[str, Any]:
    """
    Extrae de forma robusta los datos enviados tanto en formato JSON
    (Content-Type: application/json) como en formulario (application/x-www-form-urlencoded o multipart/form-data).
    """
    datos_json = request.get_json(silent=True)
    if isinstance(datos_json, dict) and datos_json:
        return datos_json
    if request.form:
        return request.form.to_dict()
    return {}


def respuesta_exito(datos: Any, codigo: int = 200) -> Tuple[Response, int]:
    """Retorna una respuesta JSON estandarizada para operaciones exitosas."""
    return jsonify(datos), codigo


def respuesta_error(mensaje: str, codigo: int = 400) -> Tuple[Response, int]:
    """
    Retorna una respuesta JSON estandarizada para errores de validación o servidor.
    Estructura uniforme: {"error": True, "mensaje": "...", "status": codigo}.
    """
    return jsonify({
        "error": True,
        "mensaje": mensaje,
        "status": codigo
    }), codigo


# =============================================================================
# MANEJADORES GLOBALES DE ERRORES HTTP (400, 401, 404, 405, 500)
# =============================================================================
@app.errorhandler(400)
def error_bad_request(e) -> Tuple[Response, int]:
    """Manejo global de error 400 Bad Request."""
    msg = getattr(e, "description", "Solicitud incorrecta o parámetros inválidos.")
    return respuesta_error(msg, 400)


@app.errorhandler(401)
def error_unauthorized(e) -> Tuple[Response, int]:
    """Manejo global de error 401 Unauthorized."""
    msg = getattr(e, "description", "No autorizado. Inicie sesión para continuar.")
    return respuesta_error(msg, 401)


@app.errorhandler(404)
def error_not_found(e) -> Tuple[Response, int]:
    """Manejo global de error 404 Not Found."""
    return respuesta_error("El recurso solicitado no fue encontrado en el servidor.", 404)


@app.errorhandler(405)
def error_method_not_allowed(e) -> Tuple[Response, int]:
    """Manejo global de error 405 Method Not Allowed."""
    return respuesta_error("Método HTTP no permitido para la ruta solicitada.", 405)


@app.errorhandler(500)
def error_internal_server(e) -> Tuple[Response, int]:
    """Manejo global de error 500 Internal Server Error."""
    return respuesta_error("Error interno del servidor.", 500)


# =============================================================================
# RUTAS DE AUTENTICACIÓN Y ROLES DE NAVEGACIÓN
# =============================================================================
@app.route("/")
def home() -> Response:
    """Redirige al dashboard del rol en sesión o al /login."""
    role = session.get("role")
    if role == "admin":
        return redirect(url_for("admin_dashboard"))
    elif role == "teacher":
        return redirect(url_for("teacher_dashboard"))
    elif role == "student":
        return redirect(url_for("student_dashboard"))
    return redirect(url_for("login_view"))


@app.route("/login")
def login_view() -> str:
    """Vista inicial de inicio de sesión."""
    return render_template("login.html")


@app.route("/admin")
def admin_dashboard():
    """Vista exclusiva para Administrador (Rector)."""
    if session.get("role") != "admin":
        return redirect(url_for("login_view"))
    return render_template("admin.html")


@app.route("/teacher")
def teacher_dashboard():
    """Vista exclusiva para Docentes."""
    if session.get("role") != "teacher":
        return redirect(url_for("login_view"))
    return render_template("teacher.html")


@app.route("/student")
def student_dashboard():
    """Vista exclusiva para Estudiantes."""
    if session.get("role") != "student":
        return redirect(url_for("login_view"))
    return render_template("student.html")


@app.route("/logout")
def logout_view() -> Response:
    """Cierra la sesión activa del usuario."""
    session.clear()
    return redirect(url_for("login_view"))


@app.route("/api/login", methods=["POST"])
def api_login() -> Tuple[Response, int]:
    """
    Endpoint de inicio de sesión integrando la lógica estricta de mb-system:
    - Verificación de credenciales (username/email + Argon2 hash).
    - Conteo de intentos fallidos y bloqueo tras MAX_LOGIN_ATTEMPTS (3 intentos).
    - Registro de historial de sesiones en `login_history`.
    - Generación de access_token y refresh_token JWT.
    - Redirección según rol (Admin -> /admin, Teacher -> /teacher, Student -> /student).
    """
    datos = obtener_datos_peticion()
    usuario_input = (datos.get("usuario") or datos.get("username") or "").strip()
    clave_input = (datos.get("clave") or datos.get("password") or "").strip()

    if not usuario_input or not clave_input:
        return respuesta_error("Por favor ingresa tu usuario/correo y contraseña.", 400)

    db = get_sqlalchemy_db()
    ip_addr = request.remote_addr or request.headers.get("X-Forwarded-For")
    user_agent = request.headers.get("User-Agent", "")

    def registrar_intento(exito: bool, motivo: str = None, uid=None, jti=None):
        lh = LoginHistory(
            user_id=uid,
            username_attempted=usuario_input,
            session_jti=jti,
            ip_address=ip_addr,
            user_agent=user_agent,
            success=exito,
            failure_reason=motivo
        )
        db.add(lh)
        db.commit()

    # Consultar usuario por username o email
    user = db.query(User).filter(
        (User.username.ilike(usuario_input)) | (User.email.ilike(usuario_input))
    ).first()

    if user is None:
        registrar_intento(False, "usuario_no_existe")
        return respuesta_error("Usuario o contraseña incorrectos.", 401)

    # Verificar bloqueo de cuenta
    if user.locked_until and user.locked_until > datetime.utcnow():
        registrar_intento(False, "cuenta_bloqueada", user.id)
        tiempo_bloqueo = user.locked_until.strftime("%H:%M:%S")
        return respuesta_error(
            f"Cuenta bloqueada temporalmente por múltiples intentos fallidos (hasta {tiempo_bloqueo}).",
            423
        )

    # Verificar activación de cuenta
    if not user.is_active:
        registrar_intento(False, "cuenta_inactiva", user.id)
        return respuesta_error("Cuenta desactivada. Contacte al Administrador.", 403)

    # Verificar contraseña con Argon2 (mb-system)
    if not verify_password(clave_input, user.hashed_password):
        user.failed_attempts += 1
        if user.failed_attempts >= settings.MAX_LOGIN_ATTEMPTS:
            user.locked_until = datetime.utcnow() + timedelta(minutes=settings.LOCKOUT_MINUTES)
            user.failed_attempts = 0
            db.commit()
            registrar_intento(False, "cuenta_bloqueada_ahora", user.id)
            return respuesta_error(
                f"Demasiados intentos fallidos. Su cuenta ha sido bloqueada por {settings.LOCKOUT_MINUTES} minutos.",
                423
            )
        db.commit()
        registrar_intento(False, "password_incorrecta", user.id)
        intentos_restantes = settings.MAX_LOGIN_ATTEMPTS - user.failed_attempts
        return respuesta_error(
            f"Usuario o contraseña incorrectos. Intentos restantes antes del bloqueo: {intentos_restantes}",
            401
        )

    # Login exitoso
    user.failed_attempts = 0
    user.locked_until = None
    db.commit()

    role_val = user.role.value if hasattr(user.role, 'value') else str(user.role)
    access_token = create_access_token(subject=user.username, role=role_val)
    jti = str(uuid.uuid4())
    expires_at = datetime.utcnow() + timedelta(minutes=settings.REFRESH_TOKEN_EXPIRE_MINUTES)
    refresh_token = create_refresh_token(subject=user.username, jti=jti, expires_at=expires_at)

    db.add(RefreshToken(jti=jti, user_id=user.id, expires_at=expires_at))
    registrar_intento(True, None, user.id, jti)

    # Redirección basada en rol
    role_norm = role_val.lower()
    if role_norm == "admin":
        redirect_url = "/admin"
        app_role = "admin"
    elif role_norm in ("teacher", "docente"):
        redirect_url = "/teacher"
        app_role = "teacher"
    else:
        redirect_url = "/student"
        app_role = "student"

    session["role"] = app_role
    session["user_id"] = user.id
    session["user_name"] = user.username
    session["username"] = user.username
    session["access_token"] = access_token
    session["refresh_token"] = refresh_token

    return respuesta_exito({
        "mensaje": f"Bienvenido(a) {user.username}",
        "role": app_role,
        "redirect": redirect_url,
        "access_token": access_token,
        "refresh_token": refresh_token
    })


@app.route("/api/me", methods=["GET"])
def api_me() -> Tuple[Response, int]:
    """Retorna el perfil del usuario autenticado en la sesión actual con sus datos académicos vinculados."""
    role = session.get("role")
    user_id = session.get("user_id")

    if not role or not user_id:
        return respuesta_error("No hay una sesión activa.", 401)

    db_sqla = get_sqlalchemy_db()
    user = db_sqla.get(User, user_id)
    if user:
        role_exact = user.role.value if hasattr(user.role, 'value') else str(user.role)
        app_role = session.get("role", role_exact.lower())

        resp_data = {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "role": app_role,
            "role_exact": role_exact,
            "user_id": user.id,
            "user_name": user.username,
            "nombre": user.username,
            "created_at": user.created_at.isoformat() if user.created_at else None
        }

        # Correlacionar con universidad.db para enriquecer datos académicos
        db_sqlite = get_db()
        cursor = db_sqlite.cursor()

        if app_role in ("student", "estudiante"):
            cursor.execute("""
                SELECT e.*, c.nombre as carrera_nombre 
                FROM estudiantes e 
                LEFT JOIN carreras c ON e.carrera_id = c.id
                WHERE e.user_id = ? OR e.username = ? OR e.email = ?;
            """, (user.id, user.username, user.email))
            est = cursor.fetchone()
            if est:
                resp_data.update({
                    "id": est["id"],  # Código académico ej: EST-001
                    "estudiante_id": est["id"],
                    "nombre": est["nombre"],
                    "documento": est["documento"] or "",
                    "matricula": est["matricula"],
                    "carrera_id": est["carrera_id"],
                    "carrera_nombre": est["carrera_nombre"] or est["carrera_id"],
                    "semestre": est["semestre"],
                    "grupo": est["grupo"] or "G1",
                    "promedio": float(est["promedio"] or 0.0),
                    "estado": est["estado"],
                    "estado_pago": est["estado_pago"],
                    "foto_avatar": est["foto_avatar"]
                })
        elif app_role in ("teacher", "docente"):
            cursor.execute("""
                SELECT p.*, c.nombre as carrera_nombre 
                FROM profesores p
                LEFT JOIN carreras c ON p.carrera_principal = c.id
                WHERE p.user_id = ? OR p.username = ? OR p.email = ?;
            """, (user.id, user.username, user.email))
            doc = cursor.fetchone()
            if doc:
                resp_data.update({
                    "id": doc["id"],  # Código académico ej: DOC-001
                    "docente_id": doc["id"],
                    "nombre": doc["nombre"],
                    "documento": doc["documento"],
                    "carrera_principal": doc["carrera_principal"],
                    "carrera_nombre": doc["carrera_nombre"] or doc["carrera_principal"],
                    "titulo_academico": doc["titulo_academico"],
                    "telefono": doc["telefono"],
                    "estado": doc["estado"]
                })

        return respuesta_exito(resp_data)

    # Si no está en SQLAlchemy pero hay sesión de admin
    if role == "admin":
        return respuesta_exito({
            "role": "admin",
            "user_id": user_id,
            "nombre": session.get("user_name", "Administrador"),
            "email": "admin@universidad.edu"
        })

    return respuesta_error("Usuario no encontrado", 404)


@app.route("/api/docentes/<string:id>/dashboard", methods=["GET"])
def docente_dashboard_api(id: str) -> Tuple[Response, int]:
    """Retorna la información del panel del docente con sus asignaturas asignadas e inscritos."""
    db = get_db()
    cursor = db.cursor()

    cursor.execute("SELECT * FROM profesores WHERE id = ?;", (id,))
    doc_row = cursor.fetchone()
    if not doc_row:
        return respuesta_error("Docente no encontrado", 404)
    doc = dict(doc_row)

    cursor.execute("""
        SELECT a.*, COUNT(i.estudiante_id) as inscritos
        FROM asignaturas a
        LEFT JOIN inscripciones i ON a.id = i.asignatura_id
        WHERE a.docente = ?
        GROUP BY a.id;
    """, (doc["nombre"],))
    asgs = [dict(r) for r in cursor.fetchall()]

    return respuesta_exito({
        "docente": doc,
        "total_asignaturas": len(asgs),
        "asignaturas": asgs
    })


# =============================================================================
# ENDPOINTS RESTful (API JSON)
# =============================================================================

@app.route("/api/dashboard", methods=["GET"])
def obtener_dashboard() -> Tuple[Response, int]:
    """Obtiene métricas agregadas avanzadas y estadísticas del sistema para el administrador."""
    db = get_db()
    cursor = db.cursor()

    total_estudiantes = cursor.execute("SELECT COUNT(*) FROM estudiantes;").fetchone()[0]
    promedio_general = cursor.execute("SELECT AVG(promedio) FROM estudiantes;").fetchone()[0] or 0.0
    estudiantes_riesgo = cursor.execute("SELECT COUNT(*) FROM estudiantes WHERE estado = 'En Riesgo';").fetchone()[0]

    # Tasa de aprobación global de inscripciones (nota >= 3.5)
    total_inscripciones = cursor.execute("SELECT COUNT(*) FROM inscripciones;").fetchone()[0] or 1
    aprobadas = cursor.execute("SELECT COUNT(*) FROM inscripciones WHERE nota >= 3.5;").fetchone()[0]
    tasa_aprobacion = round((aprobadas / total_inscripciones) * 100, 1)

    # Métricas del catálogo docente y crediticio
    total_docentes = cursor.execute("SELECT COUNT(DISTINCT docente) FROM asignaturas;").fetchone()[0]
    total_creditos_catalog = cursor.execute("SELECT SUM(creditos) FROM asignaturas;").fetchone()[0] or 0

    # Distribución de estudiantes y cupos por carrera (Límite 30)
    cursor.execute("""
        SELECT c.id, c.nombre, c.codigo, c.color, c.cupos_maximos, COUNT(e.id) as cantidad,
               (c.cupos_maximos - COUNT(e.id)) as cupos_disponibles
        FROM carreras c
        LEFT JOIN estudiantes e ON c.id = e.carrera_id
        GROUP BY c.id
        ORDER BY c.nombre ASC;
    """)
    distribucion_carreras = [dict(row) for row in cursor.fetchall()]

    # Promedio acumulado comparativo por carrera
    cursor.execute("""
        SELECT c.nombre, c.codigo, c.color, ROUND(AVG(e.promedio), 2) as promedio_carrera
        FROM carreras c
        LEFT JOIN estudiantes e ON c.id = e.carrera_id
        GROUP BY c.id
        ORDER BY promedio_carrera DESC;
    """)
    promedio_carreras = [dict(row) for row in cursor.fetchall()]

    # Distribución de estudiantes por semestre (1º a 8º)
    cursor.execute("""
        SELECT semestre, COUNT(*) as cantidad
        FROM estudiantes
        GROUP BY semestre
        ORDER BY semestre ASC;
    """)
    estudiantes_semestre = [dict(row) for row in cursor.fetchall()]

    # Lista única de los 20 docentes activos
    cursor.execute("SELECT DISTINCT docente FROM asignaturas ORDER BY docente ASC;")
    lista_docentes = [row[0] for row in cursor.fetchall()]

    return respuesta_exito({
        "totalEstudiantes": total_estudiantes,
        "promedioGeneral": round(promedio_general, 2),
        "estudiantesRiesgo": estudiantes_riesgo,
        "tasaAprobacion": tasa_aprobacion,
        "totalDocentes": total_docentes,
        "totalCreditos": total_creditos_catalog,
        "distribucionCarreras": distribucion_carreras,
        "promedioCarreras": promedio_carreras,
        "estudiantesSemestre": estudiantes_semestre,
        "listaDocentes": lista_docentes
    })


@app.route("/api/carreras", methods=["GET"])
def obtener_carreras() -> Tuple[Response, int]:
    """Retorna el catálogo de las 5 carreras profesionales."""
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT * FROM carreras ORDER BY nombre ASC;")
    carreras = [dict(row) for row in cursor.fetchall()]
    return respuesta_exito(carreras)


@app.route("/api/asignaturas", methods=["GET"])
def obtener_asignaturas() -> Tuple[Response, int]:
    """
    Retorna asignaturas filtradas opcionalmente por:
    - nivel: 1, 2, 3
    - carrera_id: ISW, MED, ADM, DER, ARQ
    - docente: nombre exacto de docente
    - tipo: 'exclusiva' | 'compartida'
    - q: búsqueda por nombre o código
    """
    nivel = request.args.get("nivel", type=int)
    carrera_id = request.args.get("carrera_id", type=str)
    docente = request.args.get("docente", type=str)
    tipo = request.args.get("tipo", type=str)
    q = request.args.get("q", type=str)

    query = """
        SELECT a.*, c.nombre as carrera_nombre 
        FROM asignaturas a 
        LEFT JOIN carreras c ON a.carrera_id = c.id 
        WHERE 1=1
    """
    params: List[Any] = []

    if nivel:
        query += " AND a.nivel = ?"
        params.append(nivel)

    if carrera_id:
        query += " AND (a.carrera_id = ? OR a.carreras_compartidas LIKE ?)"
        params.extend([carrera_id, f"%{carrera_id}%"])

    if docente:
        query += " AND a.docente = ?"
        params.append(docente)

    if tipo:
        query += " AND a.tipo = ?"
        params.append(tipo)

    if q:
        query += " AND (a.nombre LIKE ? OR a.codigo LIKE ? OR a.docente LIKE ?)"
        busqueda = f"%{q.strip()}%"
        params.extend([busqueda, busqueda, busqueda])

    query += " ORDER BY a.nivel ASC, a.nombre ASC;"

    db = get_db()
    cursor = db.cursor()
    cursor.execute(query, params)
    asignaturas = [dict(row) for row in cursor.fetchall()]
    return respuesta_exito(asignaturas)


@app.route("/api/grupos", methods=["GET"])
def obtener_grupos_estudio() -> Tuple[Response, int]:
    """
    Retorna la lista de grupos académicos de estudio organizados por Carrera, Semestres y Nivel.
    Garantiza el límite de máximo 15 estudiantes por aula/sección.
    """
    carrera_id = request.args.get("carrera_id", type=str)
    grupo_filtro = request.args.get("grupo", type=str)

    db = get_db()
    cursor = db.cursor()

    query = """
        SELECT a.id as asignatura_id, a.codigo, a.nombre as asignatura_nombre, a.nivel, a.tipo,
               a.carrera_id, a.carreras_compartidas, a.docente, a.horario, a.grupo, a.aula,
               COUNT(i.estudiante_id) as inscritos
        FROM asignaturas a
        LEFT JOIN inscripciones i ON a.id = i.asignatura_id
        WHERE 1=1
    """
    params: List[Any] = []

    if carrera_id:
        query += " AND (a.carrera_id = ? OR a.carreras_compartidas LIKE ?)"
        params.extend([carrera_id, f"%{carrera_id}%"])

    if grupo_filtro:
        query += " AND a.grupo = ?"
        params.append(grupo_filtro)

    query += " GROUP BY a.id ORDER BY a.nivel ASC, a.codigo ASC;"

    cursor.execute(query, params)
    rows = cursor.fetchall()

    grupos_resultado = []
    for r in rows:
        nivel = r["nivel"]
        if nivel == 1:
            semestres_txt = "1º y 2º Semestre (Fundamentos)"
        elif nivel == 2:
            semestres_txt = "3º a 5º Semestre (Intermedio)"
        elif nivel == 3:
            semestres_txt = "6º a 8º Semestre (Avanzado)"
        else:
            semestres_txt = "9º y 10º Semestre (Especialización/Internado)"
        inscritos = r["inscritos"]
        capacidad_max = 10 if r["tipo"] == "exclusiva" else 15
        
        grupos_resultado.append({
            "codigo_seccion": f"SEC-{r['codigo']}-{r['grupo']}",
            "asignatura_id": r["asignatura_id"],
            "codigo": r["codigo"],
            "nombre": r["asignatura_nombre"],
            "nivel": nivel,
            "semestres_destino": semestres_txt,
            "tipo": r["tipo"],
            "carrera_id": r["carrera_id"] or "COMPARTIDA",
            "docente": r["docente"],
            "horario": r["horario"],
            "grupo": r["grupo"],
            "aula": r["aula"],
            "capacidad_aula": capacidad_max,
            "inscritos": inscritos,
            "cupos_libres": max(0, capacidad_max - inscritos),
            "estado_aula": f"{capacidad_max}/{capacidad_max} Llena" if inscritos >= capacidad_max else f"{inscritos}/{capacidad_max} Ocupados"
        })

    return respuesta_exito(grupos_resultado)


@app.route("/api/estudiantes", methods=["GET"])
def obtener_estudiantes() -> Tuple[Response, int]:
    """
    Retorna la lista de estudiantes con filtrado dinámico (carrera, semestre, estado, estado_pago, q).
    """
    carrera_id = request.args.get("carrera_id", type=str)
    semestre = request.args.get("semestre", type=int)
    estado = request.args.get("estado", type=str)
    estado_pago = request.args.get("estado_pago", type=str)
    q = request.args.get("q", type=str)

    query = """
        SELECT e.*, c.nombre as carrera_nombre, c.codigo as carrera_codigo, c.color as carrera_color
        FROM estudiantes e
        JOIN carreras c ON e.carrera_id = c.id
        WHERE 1=1
    """
    params: List[Any] = []

    if carrera_id:
        query += " AND e.carrera_id = ?"
        params.append(carrera_id)

    if semestre:
        query += " AND e.semestre = ?"
        params.append(semestre)

    if estado:
        query += " AND e.estado = ?"
        params.append(estado)

    if estado_pago:
        query += " AND e.estado_pago = ?"
        params.append(estado_pago)

    if q:
        query += " AND (e.nombre LIKE ? OR e.matricula LIKE ? OR e.email LIKE ?)"
        busqueda = f"%{q.strip()}%"
        params.extend([busqueda, busqueda, busqueda])

    query += " ORDER BY e.nombre ASC;"

    db = get_db()
    cursor = db.cursor()
    cursor.execute(query, params)
    estudiantes = [dict(row) for row in cursor.fetchall()]
    return respuesta_exito(estudiantes)


@app.route("/api/estudiantes/<string:id>", methods=["GET"])
def obtener_detalle_estudiante(id: str) -> Tuple[Response, int]:
    """Obtiene información detallada y el kardex de asignaturas de un estudiante."""
    db = get_db()
    cursor = db.cursor()

    cursor.execute("""
        SELECT e.*, c.nombre as carrera_nombre, c.codigo as carrera_codigo, c.color as carrera_color
        FROM estudiantes e
        JOIN carreras c ON e.carrera_id = c.id
        WHERE e.id = ?;
    """, (id,))
    row = cursor.fetchone()

    if not row:
        return respuesta_error("Estudiante no encontrado", 404)

    estudiante = dict(row)

    cursor.execute("""
        SELECT i.id as inscripcion_id, i.nota, i.periodo, a.id as asignatura_id, a.codigo, a.nombre, a.creditos, a.nivel, a.docente
        FROM inscripciones i
        JOIN asignaturas a ON i.asignatura_id = a.id
        WHERE i.estudiante_id = ?
        ORDER BY a.nivel ASC, a.nombre ASC;
    """, (id,))
    estudiante["inscripciones"] = [dict(r) for r in cursor.fetchall()]

    return respuesta_exito(estudiante)


@app.route("/api/estudiantes", methods=["POST"])
def crear_estudiante() -> Tuple[Response, int]:
    """Registra un nuevo estudiante con validación estricta de parámetros."""
    datos = obtener_datos_peticion()
    nombre = datos.get("nombre", "").strip()
    carrera_id = datos.get("carrera_id", "").strip()

    if not nombre or not carrera_id:
        return respuesta_error("El nombre y la carrera son campos obligatorios", 400)

    db = get_db()
    cursor = db.cursor()

    # Verificar límite estricto de 30 cupos por carrera
    count_carrera = cursor.execute("SELECT COUNT(*) FROM estudiantes WHERE carrera_id = ?;", (carrera_id,)).fetchone()[0]
    if count_carrera >= 30:
        return respuesta_error(f"La carrera '{carrera_id}' ha alcanzado el límite máximo de 30 cupos (30/30 ocupados).", 400)

    total = cursor.execute("SELECT COUNT(*) FROM estudiantes;").fetchone()[0] + 1
    nuevo_id = f"EST-{total:03d}"
    semestre = int(datos.get("semestre", 1))
    matricula = f"2026-{carrera_id}-{total:03d}"
    email = datos.get("email") or f"{nombre.lower().replace(' ', '.')}@universidad.edu"
    telefono = datos.get("telefono") or "+52 55 5555-5555"
    estado = datos.get("estado") or "Activo"
    avatar = f"https://api.dicebear.com/7.x/bottts/svg?seed={nuevo_id}"

    with db:
        db.execute("""
            INSERT INTO estudiantes (id, matricula, nombre, email, telefono, carrera_id, semestre, estado, promedio, foto_avatar)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, (nuevo_id, matricula, nombre, email, telefono, carrera_id, semestre, estado, 0.0, avatar))

    return respuesta_exito({"mensaje": "Estudiante registrado con éxito", "id": nuevo_id}, 201)


@app.route("/api/estudiantes/<string:id>/notas", methods=["POST"])
def registrar_nota(id: str) -> Tuple[Response, int]:
    """
    Registra o actualiza una calificación para el estudiante.
    Recalcula automáticamente el promedio ponderado y actualiza su estado académico.
    """
    datos = obtener_datos_peticion()
    asignatura_id = datos.get("asignatura_id")
    nota_raw = datos.get("nota")

    try:
        nota = float(nota_raw)
        if not (0.0 <= nota <= ESCALA_MAXIMA_NOTA):
            return respuesta_error("La nota debe estar entre 0.0 y 5.0", 400)
    except (ValueError, TypeError):
        return respuesta_error("Valor de nota inválido", 400)

    if not asignatura_id:
        return respuesta_error("Falta especificar el ID de la asignatura", 400)

    db = get_db()
    cursor = db.cursor()

    with db:
        existente = cursor.execute(
            "SELECT id FROM inscripciones WHERE estudiante_id = ? AND asignatura_id = ?;",
            (id, asignatura_id)
        ).fetchone()

        if existente:
            cursor.execute("UPDATE inscripciones SET nota = ? WHERE id = ?;", (nota, existente["id"]))
        else:
            cursor.execute(
                "INSERT INTO inscripciones (estudiante_id, asignatura_id, nota, periodo) VALUES (?, ?, ?, ?);",
                (id, asignatura_id, nota, "2026-1")
            )

        # Recalcular Promedio Ponderado
        registros = cursor.execute("""
            SELECT i.nota, a.creditos
            FROM inscripciones i
            JOIN asignaturas a ON i.asignatura_id = a.id
            WHERE i.estudiante_id = ?;
        """, (id,)).fetchall()

        if registros:
            puntos = sum(row["nota"] * row["creditos"] for row in registros)
            creditos = sum(row["creditos"] for row in registros)
            nuevo_promedio = round(puntos / creditos, 2)
        else:
            nuevo_promedio = 0.0

        nuevo_estado = "En Riesgo" if nuevo_promedio < NOTA_MINIMA_APROBATORIA else "Activo"

        cursor.execute("UPDATE estudiantes SET promedio = ?, estado = ? WHERE id = ?;", (nuevo_promedio, nuevo_estado, id))

    return respuesta_exito({
        "mensaje": "Calificación registrada correctamente",
        "nuevoPromedio": nuevo_promedio,
        "nuevoEstado": nuevo_estado
    })


@app.route("/api/estudiantes/<string:id>/solicitar-cambio", methods=["POST"])
@app.route("/api/estudiantes/<string:id>/cambiar-grupo", methods=["POST"])
def solicitar_cambio_grupo_estudiante(id: str) -> Tuple[Response, int]:
    """
    Registra una solicitud formal de cambio de horario/grupo para un estudiante.
    Restringe la modificación directa inmediata y encola un registro 'PENDIENTE'
    que requerirá la aprobación de Administración.
    """
    datos = obtener_datos_peticion()
    asignatura_id = datos.get("asignatura_id")
    nuevo_grupo = datos.get("nuevo_grupo", "").strip().upper()
    motivo = datos.get("motivo", "Solicitud de cambio de horario/grupo por motivos académicos o personales.").strip()

    if not asignatura_id or not nuevo_grupo:
        return respuesta_error("Debe especificar la asignatura y el nuevo grupo de destino.", 400)

    db = get_db()
    cursor = db.cursor()

    # 1. Verificar estudiante
    cursor.execute("SELECT * FROM estudiantes WHERE id = ?;", (id,))
    est_row = cursor.fetchone()
    if not est_row:
        return respuesta_error(f"Estudiante '{id}' no encontrado.", 404)
    est = dict(est_row)

    # 2. Verificar asignatura matriculada
    cursor.execute("SELECT * FROM asignaturas WHERE id = ? OR codigo = ?;", (asignatura_id, asignatura_id))
    asg_row = cursor.fetchone()
    if not asg_row:
        return respuesta_error(f"Asignatura '{asignatura_id}' no encontrada.", 404)
    asg = dict(asg_row)
    id_asignatura_real = asg["id"]

    grupo_actual = asg.get("grupo", "G1")
    if grupo_actual == nuevo_grupo:
        return respuesta_error(f"Ya se encuentra matriculado en el Grupo {nuevo_grupo} de '{asg['nombre']}'.", 400)

    # 3. Verificar si ya existe una solicitud PENDIENTE para este estudiante y asignatura
    cursor.execute("""
        SELECT id FROM solicitudes_cambio_grupo
        WHERE estudiante_id = ? AND (asignatura_id = ? OR asignatura_id = ?) AND estado = 'PENDIENTE';
    """, (id, id_asignatura_real, asg["codigo"]))
    solicitud_existente = cursor.fetchone()
    if solicitud_existente:
        return respuesta_error(
            f"Ya tiene una solicitud pendiente de revisión por administración para la asignatura '{asg['nombre']}'.",
            400
        )

    # 4. Crear registro formal con estado PENDIENTE
    fecha_actual = datetime.now().strftime("%Y-%m-%d %H:%M")
    with db:
        cursor.execute("""
            INSERT INTO solicitudes_cambio_grupo 
                (estudiante_id, asignatura_id, grupo_actual, grupo_solicitado, motivo, estado, fecha)
            VALUES (?, ?, ?, ?, ?, 'PENDIENTE', ?);
        """, (id, id_asignatura_real, grupo_actual, nuevo_grupo, motivo, fecha_actual))
        solicitud_id = cursor.lastrowid

    return respuesta_exito({
        "mensaje": "Solicitud enviada, pendiente de revisión por administración.",
        "solicitud_id": solicitud_id,
        "id_estudiante": id,
        "estudiante_nombre": est["nombre"],
        "asignatura": asg["nombre"],
        "grupo_actual": grupo_actual,
        "grupo_solicitado": nuevo_grupo,
        "estado": "PENDIENTE",
        "fecha": fecha_actual
    }, 201)


@app.route("/api/estudiantes/<string:id>/solicitudes", methods=["GET"])
def obtener_solicitudes_estudiante(id: str) -> Tuple[Response, int]:
    """Retorna el historial de solicitudes de cambio de horario/grupo del estudiante."""
    db = get_db()
    cursor = db.cursor()
    cursor.execute("""
        SELECT s.*, a.nombre AS asignatura_nombre, a.codigo AS asignatura_codigo
        FROM solicitudes_cambio_grupo s
        JOIN asignaturas a ON (s.asignatura_id = a.id OR s.asignatura_id = a.codigo)
        WHERE s.estudiante_id = ?
        ORDER BY s.fecha DESC, s.id DESC;
    """, (id,))
    solicitudes = [dict(r) for r in cursor.fetchall()]
    return respuesta_exito({
        "total": len(solicitudes),
        "solicitudes": solicitudes
    })


@app.route("/api/admin/solicitudes-cambio", methods=["GET"])
def obtener_solicitudes_admin() -> Tuple[Response, int]:
    """Retorna todas las solicitudes de cambio de grupo registradas para el panel de Administración."""
    db = get_db()
    cursor = db.cursor()
    cursor.execute("""
        SELECT s.*, e.nombre AS estudiante_nombre, e.carrera_id, e.foto_avatar,
               a.nombre AS asignatura_nombre, a.codigo AS asignatura_codigo, a.tipo AS asignatura_tipo, a.horario AS asignatura_horario
        FROM solicitudes_cambio_grupo s
        JOIN estudiantes e ON s.estudiante_id = e.id
        JOIN asignaturas a ON (s.asignatura_id = a.id OR s.asignatura_id = a.codigo)
        ORDER BY CASE WHEN s.estado = 'PENDIENTE' THEN 0 ELSE 1 END, s.fecha DESC, s.id DESC;
    """)
    solicitudes = [dict(r) for r in cursor.fetchall()]
    pendientes = sum(1 for s in solicitudes if s["estado"] == "PENDIENTE")
    aprobadas = sum(1 for s in solicitudes if s["estado"] == "APROBADO")
    rechazadas = sum(1 for s in solicitudes if s["estado"] == "RECHAZADO")

    return respuesta_exito({
        "total": len(solicitudes),
        "pendientes": pendientes,
        "aprobadas": aprobadas,
        "rechazadas": rechazadas,
        "solicitudes": solicitudes
    })


@app.route("/api/admin/solicitudes-cambio/<int:solicitud_id>/aprobar", methods=["POST"])
def aprobar_solicitud_cambio(solicitud_id: int) -> Tuple[Response, int]:
    """
    Aprueba una solicitud de cambio de grupo:
    1. Ejecuta la reasignación en la base de datos (asignaturas.grupo).
    2. Cambia el estado a 'APROBADO' con fecha de resolución.
    3. Genera una notificación interna visible para el estudiante.
    """
    db = get_db()
    cursor = db.cursor()

    cursor.execute("SELECT * FROM solicitudes_cambio_grupo WHERE id = ?;", (solicitud_id,))
    sol_row = cursor.fetchone()
    if not sol_row:
        return respuesta_error(f"Solicitud de cambio #{solicitud_id} no encontrada.", 404)
    sol = dict(sol_row)

    if sol["estado"] != "PENDIENTE":
        return respuesta_error(f"La solicitud #{solicitud_id} ya se encuentra resuelta como '{sol['estado']}'.", 400)

    # Obtener datos de la asignatura
    cursor.execute("SELECT * FROM asignaturas WHERE id = ? OR codigo = ?;", (sol["asignatura_id"], sol["asignatura_id"]))
    asg_row = cursor.fetchone()
    asg_nombre = asg_row["nombre"] if asg_row else sol["asignatura_id"]
    asg_id = asg_row["id"] if asg_row else sol["asignatura_id"]

    fecha_resolucion = datetime.now().strftime("%Y-%m-%d %H:%M")

    with db:
        # Reasignación de grupo en la BD
        cursor.execute("UPDATE asignaturas SET grupo = ? WHERE id = ?;", (sol["grupo_solicitado"], asg_id))


        # Actualización de estado de la solicitud
        cursor.execute("""
            UPDATE solicitudes_cambio_grupo
            SET estado = 'APROBADO', fecha_resolucion = ?, respuesta_admin = 'Solicitud validada y aprobada por administración institucional.'
            WHERE id = ?;
        """, (fecha_resolucion, solicitud_id))

        # Notificación para el estudiante
        cursor.execute("""
            INSERT INTO notificaciones (estudiante_id, titulo, mensaje, tipo, fecha, leido)
            VALUES (?, ?, ?, 'academico', ?, 0);
        """, (
            sol["estudiante_id"],
            "✅ Solicitud de Cambio de Grupo APROBADA",
            f"Su solicitud de cambio al Grupo {sol['grupo_solicitado']} para la asignatura '{asg_nombre}' ha sido APROBADA por administración. Su horario oficial ha sido actualizado.",
            fecha_resolucion
        ))

    return respuesta_exito({
        "mensaje": f"Solicitud #{solicitud_id} aprobada con éxito. Estudiante reasignado al Grupo {sol['grupo_solicitado']}.",
        "solicitud_id": solicitud_id,
        "nuevo_estado": "APROBADO",
        "fecha_resolucion": fecha_resolucion
    })


@app.route("/api/admin/solicitudes-cambio/<int:solicitud_id>/rechazar", methods=["POST"])
def rechazar_solicitud_cambio(solicitud_id: int) -> Tuple[Response, int]:
    """
    Rechaza una solicitud de cambio de grupo:
    1. Cambia el estado a 'RECHAZADO' sin modificar el grupo actual del estudiante.
    2. Genera una notificación interna visible para el estudiante informando el rechazo.
    """
    db = get_db()
    cursor = db.cursor()

    cursor.execute("SELECT * FROM solicitudes_cambio_grupo WHERE id = ?;", (solicitud_id,))
    sol_row = cursor.fetchone()
    if not sol_row:
        return respuesta_error(f"Solicitud de cambio #{solicitud_id} no encontrada.", 404)
    sol = dict(sol_row)

    if sol["estado"] != "PENDIENTE":
        return respuesta_error(f"La solicitud #{solicitud_id} ya se encuentra resuelta como '{sol['estado']}'.", 400)

    datos = obtener_datos_peticion()
    motivo_rechazo = datos.get("motivo", "No cumple con criterios de aforo o planificación académica.").strip()

    cursor.execute("SELECT * FROM asignaturas WHERE id = ?;", (sol["asignatura_id"],))
    asg_row = cursor.fetchone()
    asg_nombre = asg_row["nombre"] if asg_row else sol["asignatura_id"]

    fecha_resolucion = datetime.now().strftime("%Y-%m-%d %H:%M")

    with db:
        # Estado RECHAZADO sin alterar el grupo de clase
        cursor.execute("""
            UPDATE solicitudes_cambio_grupo
            SET estado = 'RECHAZADO', fecha_resolucion = ?, respuesta_admin = ?
            WHERE id = ?;
        """, (fecha_resolucion, motivo_rechazo, solicitud_id))

        # Notificación para el estudiante
        cursor.execute("""
            INSERT INTO notificaciones (estudiante_id, titulo, mensaje, tipo, fecha, leido)
            VALUES (?, ?, ?, 'academico', ?, 0);
        """, (
            sol["estudiante_id"],
            "❌ Solicitud de Cambio de Grupo RECHAZADA",
            f"Su solicitud de cambio al Grupo {sol['grupo_solicitado']} para la asignatura '{asg_nombre}' ha sido RECHAZADA por administración. Motivo: {motivo_rechazo}.",
            fecha_resolucion
        ))

    return respuesta_exito({
        "mensaje": f"Solicitud #{solicitud_id} rechazada por administración sin alterar el grupo.",
        "solicitud_id": solicitud_id,
        "nuevo_estado": "RECHAZADO",
        "fecha_resolucion": fecha_resolucion
    })



@app.route("/api/estudiantes/<string:id>/notificaciones", methods=["GET"])
def obtener_notificaciones_estudiante(id: str) -> Tuple[Response, int]:
    """Retorna la lista de notificaciones y alertas de pago para el estudiante especificado."""
    db = get_db()
    cursor = db.cursor()

    cursor.execute("""
        SELECT * FROM notificaciones 
        WHERE estudiante_id = ? 
        ORDER BY fecha DESC, id DESC;
    """, (id,))
    notifs = [dict(r) for r in cursor.fetchall()]
    no_leidas = sum(1 for n in notifs if n["leido"] == 0)

    return respuesta_exito({
        "total": len(notifs),
        "no_leidas": no_leidas,
        "notificaciones": notifs
    })


@app.route("/api/notificaciones/<int:notif_id>/leida", methods=["POST"])
def marcar_notificacion_leida(notif_id: int) -> Tuple[Response, int]:
    """Marca una notificación como leída."""
    db = get_db()
    cursor = db.cursor()
    with db:
        cursor.execute("UPDATE notificaciones SET leido = 1 WHERE id = ?;", (notif_id,))
    return respuesta_exito({"mensaje": "Notificación marcada como leída."})


@app.route("/api/estudiantes/<string:id>/estado-pago", methods=["POST"])
def actualizar_estado_pago(id: str) -> Tuple[Response, int]:
    """
    Permite al administrador modificar el estado financiero del estudiante
    ('Al día', 'Pendiente', 'Bloqueado') y genera una notificación/alerta automática.
    """
    datos = obtener_datos_peticion()
    nuevo_estado_pago = datos.get("estado_pago", "").strip()
    titulo_notif = datos.get("titulo", "").strip()
    mensaje_notif = datos.get("mensaje", "").strip()

    if nuevo_estado_pago not in ("Al día", "Pendiente", "Bloqueado"):
        return respuesta_error("El estado de pago debe ser: 'Al día', 'Pendiente' o 'Bloqueado'.", 400)

    db = get_db()
    cursor = db.cursor()

    cursor.execute("SELECT * FROM estudiantes WHERE id = ?;", (id,))
    est = cursor.fetchone()
    if not est:
        return respuesta_error(f"Estudiante '{id}' no encontrado.", 404)

    fecha_hoy = datetime.now().strftime("%Y-%m-%d %H:%M")

    with db:
        cursor.execute("UPDATE estudiantes SET estado_pago = ? WHERE id = ?;", (nuevo_estado_pago, id))

        if mensaje_notif or nuevo_estado_pago != dict(est)["estado_pago"]:
            titulo = titulo_notif or (
                "🚨 ALERTA FINANCIERA: Acceso Bloqueado" if nuevo_estado_pago == "Bloqueado"
                else ("⚠️ AVISO DE COBRANZA: Pago Pendiente" if nuevo_estado_pago == "Pendiente" else "✅ Estado Financiero Actualizado: Al Día")
            )
            contenido = mensaje_notif or (
                "Se ha registrado un bloqueo financiero en su cuenta por concepto de arancel/matricula. Por favor acuda a Tesorería Central." if nuevo_estado_pago == "Bloqueado"
                else ("Tiene una cuota pendiente de pago. Le solicitamos regularizar su saldo para evitar bloqueos." if nuevo_estado_pago == "Pendiente" else "Su estado financiero ha sido actualizado a 'Al Día'. Gracias por mantener sus pagos conformes.")
            )
            cursor.execute("""
                INSERT INTO notificaciones (estudiante_id, titulo, mensaje, tipo, fecha, leido)
                VALUES (?, ?, ?, ?, ?, 0);
            """, (id, titulo, contenido, "pago", fecha_hoy))

    return respuesta_exito({
        "mensaje": f"Estado financiero de {dict(est)['nombre']} actualizado a '{nuevo_estado_pago}' exitosamente.",
        "nuevoEstadoPago": nuevo_estado_pago
    })


@app.route("/api/estudiantes/<string:id>/horario", methods=["GET"])
def obtener_horario_estudiante(id: str) -> Tuple[Response, int]:
    """Retorna la matriz de horario individual semanal para el estudiante especificado."""
    db = get_db()
    cursor = db.cursor()

    cursor.execute("""
        SELECT a.id, a.codigo, a.nombre, a.creditos, a.nivel, a.tipo, a.docente, a.horario, a.grupo, a.aula
        FROM inscripciones i
        JOIN asignaturas a ON i.asignatura_id = a.id
        WHERE i.estudiante_id = ?
        ORDER BY a.nivel ASC;
    """, (id,))
    materias = [dict(r) for r in cursor.fetchall()]

    dias = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes"]
    bloques = [
        {"id": "b1", "hora": "07:00-09:00", "label": "07:00 AM - 09:00 AM"},
        {"id": "b2", "hora": "09:00-11:00", "label": "09:00 AM - 11:00 AM"},
        {"id": "b3", "hora": "10:00-12:00", "label": "10:00 AM - 12:00 PM"}
    ]

    matriz = {b["hora"]: {d: [] for d in dias} for b in bloques}

    for m in materias:
        horario = m["horario"]
        for dia_abr, dia_full in [("Lun", "Lunes"), ("Mar", "Martes"), ("Mié", "Miércoles"), ("Jue", "Jueves"), ("Vie", "Viernes")]:
            if dia_abr in horario:
                for b in bloques:
                    if b["hora"] in horario:
                        matriz[b["hora"]][dia_full].append(m)

    return respuesta_exito({
        "estudiante_id": id,
        "total_materias": len(materias),
        "materias": materias,
        "matriz_horario": matriz
    })


@app.route("/api/grupos/<string:asignatura_id>/estudiantes", methods=["GET"])
def obtener_estudiantes_de_grupo(asignatura_id: str) -> Tuple[Response, int]:
    """Retorna la nómina de estudiantes inscritos en una asignatura y grupo específico."""
    grupo = request.args.get("grupo", "").strip()

    db = get_db()
    cursor = db.cursor()

    query = """
        SELECT e.id, e.matricula, e.nombre, e.email, e.telefono, e.carrera_id, e.semestre, e.estado, e.promedio, e.foto_avatar,
               c.nombre as carrera_nombre, i.nota
        FROM inscripciones i
        JOIN estudiantes e ON i.estudiante_id = e.id
        JOIN carreras c ON e.carrera_id = c.id
        JOIN asignaturas a ON i.asignatura_id = a.id
        WHERE i.asignatura_id = ?
    """
    params = [asignatura_id]

    if grupo:
        query += " AND a.grupo = ?"
        params.append(grupo)

    query += " ORDER BY e.nombre ASC;"

    cursor.execute(query, params)
    estudiantes = [dict(r) for r in cursor.fetchall()]

    return respuesta_exito({
        "asignatura_id": asignatura_id,
        "grupo": grupo or "Todos",
        "total_inscritos": len(estudiantes),
        "estudiantes": estudiantes
    })


@app.route("/api/reset-db", methods=["POST"])
def reiniciar_base_datos() -> Tuple[Response, int]:
    """Restablece la base de datos de usuarios al estado limpio con el administrador MBSystem."""
    try:
        asegurar_admin_mbsystem()
        return respuesta_exito({"mensaje": "Base de datos de autenticación restablecida exitosamente con el Administrador MBSystem."})
    except Exception as e:
        return respuesta_error(f"Error al restablecer la base de datos: {str(e)}", 500)


# Mapa de etiquetas humanizadas e intuitivas para el Despacho Rectoral
ETIQUETAS_CAMPOS = {
    "id": "Código ID Único",
    "nombre": "Nombre Completo *",
    "codigo": "Código Académico *",
    "documento": "Documento Identidad / DNI *",
    "email": "Correo Institucional",
    "telefono": "Teléfono de Contacto",
    "titulo_academico": "Título / Grado Académico",
    "carrera_principal": "Carrera / Facultad de Adscripción",
    "carrera_id": "Carrera Profesional",
    "creditos": "Créditos Académicos",
    "nivel": "Nivel Curricular (1..3)",
    "tipo": "Tipo de Asignatura (Exclusiva / Compartida)",
    "docente": "Docente Responsable",
    "horario": "Bloque Horario (07:00 - 12:00)",
    "grupo": "Grupo Académico (G1, G2)",
    "aula": "Aula o Laboratorio Asignado",
    "matricula": "Número de Matrícula",
    "semestre": "Semestre Académico (1..8)",
    "estado": "Estado del Registro",
    "estado_pago": "Estado Financiero (Al día, Pendiente, Bloqueado)",
    "promedio": "Promedio Ponderado (0.0 - 5.0)",
    "duracion_semestres": "Duración de Carrera (Semestres)",
    "total_creditos": "Total Créditos del Plan",
    "cupos_maximos": "Límite Máximo de Cupos (30)",
    "color": "Color Institucional (Hex)",
    "descripcion": "Descripción del Programa",
    "icono": "Nombre Icono Lucide",
    "foto_avatar": "URL del Avatar",
    "estudiante_id": "Estudiante",
    "asignatura_id": "Asignatura",
    "nota": "Calificación Registrada (0.0 - 5.0)",
    "periodo": "Periodo Académico (ej: 2026-1)"
}


@app.route("/api/database/tablas", methods=["GET"])
def inspeccionar_base_datos() -> Tuple[Response, int]:
    """Retorna el esquema y la totalidad de registros de universidad.db para el visor interactivo rectoral."""
    db = get_db()
    cursor = db.cursor()
    
    nombres_tablas = [r[0] for r in cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name != 'sqlite_sequence';").fetchall()]
    
    resultado = {}
    for tabla in nombres_tablas:
        columnas_info = cursor.execute(f"PRAGMA table_info({tabla});").fetchall()
        columnas = [col[1] for col in columnas_info]
        registros = [dict(r) for r in cursor.execute(f"SELECT * FROM {tabla};").fetchall()]
        
        resultado[tabla] = {
            "totalRegistros": len(registros),
            "columnas": columnas,
            "columnasDetalle": [
                {
                    "nombre": col[1],
                    "etiqueta": ETIQUETAS_CAMPOS.get(col[1], col[1]),
                    "tipo": col[2],
                    "notnull": col[3],
                    "pk": col[5]
                } for col in columnas_info
            ],
            "muestra": registros
        }
        
    return respuesta_exito(resultado)


@app.route("/api/database/insertar", methods=["POST"])
def insertar_registro_bd() -> Tuple[Response, int]:
    """Permite añadir un registro dinámico a cualquier tabla permitida de la BD por el Rector."""
    datos_json = obtener_datos_peticion()
    tabla = datos_json.get("tabla")
    registro = datos_json.get("registro") or {}

    tablas_permitidas = ["carreras", "asignaturas", "estudiantes", "inscripciones", "profesores"]
    if tabla not in tablas_permitidas:
        return respuesta_error("Tabla no permitida o inválida", 400)

    if not registro:
        return respuesta_error("No se enviaron datos para insertar", 400)

    db = get_db()
    cursor = db.cursor()

    columnas = list(registro.keys())
    valores = list(registro.values())
    placeholders = ", ".join(["?"] * len(columnas))
    cols_str = ", ".join(columnas)

    query = f"INSERT INTO {tabla} ({cols_str}) VALUES ({placeholders});"

    try:
        with db:
            cursor.execute(query, valores)
        return respuesta_exito({"mensaje": f"Registro insertado con éxito en la tabla '{tabla}'."}, 201)
    except Exception as e:
        return respuesta_error(f"Error al insertar en '{tabla}': {str(e)}", 400)


# =============================================================================
# ENDPOINTS DE ADMINISTRACIÓN DE USUARIOS Y AUDITORÍA (mb-system)
# =============================================================================

@app.route("/api/admin/usuarios", methods=["GET"])
def admin_listar_usuarios() -> Tuple[Response, int]:
    """Lista todos los usuarios registrados en el sistema correlacionados con su perfil académico."""
    db_sqla = get_sqlalchemy_db()
    users = db_sqla.query(User).order_by(User.id).all()

    db_sqlite = get_db()
    cursor = db_sqlite.cursor()

    # Mapeo de estudiantes
    cursor.execute("SELECT id, matricula, documento, nombre, email, carrera_id, semestre, grupo, username, user_id FROM estudiantes;")
    estudiantes_por_user = {}
    for est in cursor.fetchall():
        d = dict(est)
        if d.get("user_id"):
            estudiantes_por_user[d["user_id"]] = d
        if d.get("username"):
            estudiantes_por_user[d["username"].lower()] = d

    # Mapeo de profesores
    cursor.execute("SELECT id, documento, nombre, email, carrera_principal, titulo_academico, username, user_id FROM profesores;")
    profesores_por_user = {}
    for prof in cursor.fetchall():
        d = dict(prof)
        if d.get("user_id"):
            profesores_por_user[d["user_id"]] = d
        if d.get("username"):
            profesores_por_user[d["username"].lower()] = d

    resultado = []
    for u in users:
        rol_val = u.role.value if hasattr(u.role, 'value') else str(u.role)
        rol_norm = rol_val.lower()

        nombre_persona = u.username
        documento_persona = ""
        detalle_academico = "Cuenta General de Sistema"

        if rol_norm in ("student", "estudiante"):
            est = estudiantes_por_user.get(u.id) or estudiantes_por_user.get(u.username.lower())
            if est:
                nombre_persona = est["nombre"]
                documento_persona = est.get("documento") or est.get("matricula", "")
                detalle_academico = f"Carrera: {est['carrera_id']} • Semestre {est['semestre']}º • Grupo {est.get('grupo', 'G1')}"
        elif rol_norm in ("teacher", "docente"):
            prof = profesores_por_user.get(u.id) or profesores_por_user.get(u.username.lower())
            if prof:
                nombre_persona = prof["nombre"]
                documento_persona = prof.get("documento", "")
                detalle_academico = f"{prof.get('titulo_academico', 'Docente')} • Dpto: {prof['carrera_principal']}"
        elif rol_norm == "admin":
            nombre_persona = "Administrador Rectoral"
            detalle_academico = "Despacho de Rectoría y Control Central"

        resultado.append({
            "id": u.id,
            "username": u.username,
            "email": u.email,
            "role": rol_val,
            "nombre": nombre_persona,
            "documento": documento_persona,
            "detalle_academico": detalle_academico,
            "is_active": u.is_active,
            "failed_attempts": u.failed_attempts,
            "locked_until": u.locked_until.isoformat() if u.locked_until else None,
            "created_at": u.created_at.isoformat() if u.created_at else None
        })

    return respuesta_exito(resultado)


@app.route("/api/admin/crear-usuario", methods=["POST"])
def admin_crear_usuario() -> Tuple[Response, int]:
    """
    Permite al Administrador registrar dinámicamente nuevas cuentas de cualquier rol
    con persistencia atómica en mb_system.db (users) y en universidad.db (estudiantes / profesores).
    """
    datos = obtener_datos_peticion()
    username = datos.get("username", "").strip()
    email = datos.get("email", "").strip().lower()
    password = datos.get("password", "").strip()
    role_str = datos.get("role", "usuario").strip().lower()

    nombre = (datos.get("nombre") or "").strip()
    identificacion = (datos.get("identificacion") or datos.get("documento") or "").strip()

    if not username or not email or not password:
        return respuesta_error("Nombre de usuario, email y contraseña son obligatorios.", 400)

    if len(password) < 6:
        return respuesta_error("La contraseña debe tener al menos 6 caracteres.", 400)

    # Si es Estudiante o Docente, nombre e identificación son obligatorios
    if role_str in ("student", "teacher", "docente", "estudiante"):
        if not nombre or not identificacion:
            return respuesta_error("El nombre completo y el número de identificación (cédula/documento) son obligatorios para este rol.", 400)
    else:
        if not nombre:
            nombre = username

    db_sqla = get_sqlalchemy_db()
    db_sqlite = get_db()
    cursor = db_sqlite.cursor()

    # 1. Validar que username o email no existan en mb_system.db
    existente_sqla = db_sqla.query(User).filter(
        (User.username.ilike(username)) | (User.email.ilike(email))
    ).first()
    if existente_sqla:
        return respuesta_error("El nombre de usuario o el correo electrónico ya se encuentran registrados.", 400)

    # 2. Validar que el número de identificación sea único antes de procesar el guardado
    if identificacion:
        cursor.execute("SELECT id, nombre FROM estudiantes WHERE documento = ? OR matricula = ?;", (identificacion, identificacion))
        est_dup = cursor.fetchone()
        if est_dup:
            return respuesta_error(f"El número de identificación '{identificacion}' ya está asignado al estudiante '{est_dup['nombre']}'.", 400)

        cursor.execute("SELECT id, nombre FROM profesores WHERE documento = ?;", (identificacion,))
        prof_dup = cursor.fetchone()
        if prof_dup:
            return respuesta_error(f"El número de identificación '{identificacion}' ya está asignado al docente '{prof_dup['nombre']}'.", 400)

    try:
        rol_enum = RoleEnum(role_str)
    except ValueError:
        rol_enum = RoleEnum.usuario

    # Validaciones específicas según el rol
    if rol_enum == RoleEnum.student:
        carrera_id = (datos.get("carrera_id") or datos.get("carrera") or "ISW").strip().upper()
        try:
            semestre = int(datos.get("semestre", 1))
            if not (1 <= semestre <= 10):
                semestre = 1
        except (ValueError, TypeError):
            semestre = 1
        grupo = (datos.get("grupo") or "G1").strip().upper()
        if grupo not in ("G1", "G2"):
            grupo = "G1"

        # Validar límite de 30 cupos por carrera
        count_carrera = cursor.execute("SELECT COUNT(*) FROM estudiantes WHERE carrera_id = ?;", (carrera_id,)).fetchone()[0]
        if count_carrera >= 30:
            return respuesta_error(f"La carrera '{carrera_id}' ha alcanzado el límite máximo de 30 cupos (30/30 ocupados).", 400)

    elif rol_enum == RoleEnum.teacher:
        carrera_prof = (datos.get("carrera_principal") or datos.get("carrera") or datos.get("departamento") or "ISW").strip().upper()
        titulo_academico = (datos.get("titulo_academico") or "Docente Titular").strip()

    # 3. TRANSACCIÓN ATÓMICA CON ROLLBACK BIDIRECCIONAL
    nuevo_usuario = User(
        username=username,
        email=email,
        hashed_password=hash_password(password),
        role=rol_enum,
        is_active=True
    )
    db_sqla.add(nuevo_usuario)

    try:
        # Flush para obtener nuevo_usuario.id sin confirmar la transacción todavía
        db_sqla.flush()

        with db_sqlite:
            if rol_enum == RoleEnum.student:
                total_est = cursor.execute("SELECT COUNT(*) FROM estudiantes;").fetchone()[0] + 1
                nuevo_est_id = f"EST-{total_est:03d}"
                while cursor.execute("SELECT 1 FROM estudiantes WHERE id = ?;", (nuevo_est_id,)).fetchone():
                    total_est += 1
                    nuevo_est_id = f"EST-{total_est:03d}"

                matricula = f"2026-{carrera_id}-{total_est:03d}"
                telefono = datos.get("telefono") or "+52 55 5555-5555"
                avatar = f"https://api.dicebear.com/7.x/bottts/svg?seed={username}"

                cursor.execute("""
                    INSERT INTO estudiantes (
                        id, matricula, documento, nombre, email, telefono, carrera_id,
                        semestre, grupo, estado, estado_pago, promedio, foto_avatar, username, user_id
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """, (
                    nuevo_est_id, matricula, identificacion, nombre, email,
                    telefono, carrera_id, semestre, grupo, 'Activo', 'Al día',
                    0.0, avatar, username, nuevo_usuario.id
                ))

            elif rol_enum == RoleEnum.teacher:
                total_prof = cursor.execute("SELECT COUNT(*) FROM profesores;").fetchone()[0] + 1
                nuevo_prof_id = f"DOC-{total_prof:03d}"
                while cursor.execute("SELECT 1 FROM profesores WHERE id = ?;", (nuevo_prof_id,)).fetchone():
                    total_prof += 1
                    nuevo_prof_id = f"DOC-{total_prof:03d}"

                telefono = datos.get("telefono") or "+52 55 5555-0000"
                cursor.execute("""
                    INSERT INTO profesores (
                        id, documento, nombre, email, telefono, titulo_academico,
                        carrera_principal, estado, username, user_id
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """, (
                    nuevo_prof_id, identificacion, nombre, email, telefono,
                    titulo_academico, carrera_prof, 'Activo', username, nuevo_usuario.id
                ))

        # Si la inserción en SQLite concluyó sin errores, confirmamos en SQLAlchemy
        db_sqla.commit()
        db_sqla.refresh(nuevo_usuario)

    except Exception as e:
        # Si falló la persistencia en universidad.db, se revierte en SQLAlchemy (mb_system.db)
        db_sqla.rollback()
        return respuesta_error(f"Error atómico al registrar datos académicos: {str(e)}", 400)

    return respuesta_exito({
        "mensaje": f"Usuario '{username}' ({rol_enum.value}) registrado exitosamente con sus datos académicos vinculados.",
        "usuario": {
            "id": nuevo_usuario.id,
            "username": nuevo_usuario.username,
            "email": nuevo_usuario.email,
            "role": nuevo_usuario.role.value,
            "nombre": nombre,
            "identificacion": identificacion
        }
    }, 201)


@app.route("/api/admin/usuarios/<int:user_id>", methods=["PUT", "DELETE"])
def admin_gestionar_usuario(user_id: int) -> Tuple[Response, int]:
    """Permite modificar o eliminar un usuario desde el panel de administración."""
    db = get_sqlalchemy_db()
    user = db.get(User, user_id)
    if not user:
        return respuesta_error("Usuario no encontrado", 404)

    if request.method == "DELETE":
        if session.get("user_id") == user.id:
            return respuesta_error("No puedes eliminar tu propia cuenta en sesión activa.", 400)

        # Limpieza coordinada en universidad.db
        db_sqlite = get_db()
        with db_sqlite:
            db_sqlite.execute("DELETE FROM estudiantes WHERE user_id = ? OR username = ?;", (user.id, user.username))
            db_sqlite.execute("DELETE FROM profesores WHERE user_id = ? OR username = ?;", (user.id, user.username))

        db.delete(user)
        db.commit()
        return respuesta_exito({"mensaje": f"Usuario #{user_id} y sus registros académicos asociados han sido eliminados exitosamente."})

    if request.method == "PUT":
        datos = obtener_datos_peticion()
        email = datos.get("email")
        role = datos.get("role")
        is_active = datos.get("is_active")
        new_password = datos.get("new_password")

        if email:
            user.email = email
        if role:
            try:
                user.role = RoleEnum(role.lower())
            except ValueError:
                pass
        if is_active is not None:
            user.is_active = bool(is_active)
        if new_password:
            user.hashed_password = hash_password(new_password)

        db.commit()
        db.refresh(user)
        return respuesta_exito({
            "mensaje": f"Usuario #{user.id} actualizado exitosamente.",
            "usuario": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "role": user.role.value,
                "is_active": user.is_active
            }
        })


@app.route("/api/admin/login-history", methods=["GET"])
def admin_historial_login() -> Tuple[Response, int]:
    """Retorna el registro completo de auditoría de inicio de sesión."""
    db = get_sqlalchemy_db()
    historial = db.query(LoginHistory).order_by(LoginHistory.login_at.desc()).limit(100).all()
    resultado = [
        {
            "id": h.id,
            "user_id": h.user_id,
            "username_attempted": h.username_attempted,
            "session_jti": h.session_jti,
            "ip_address": h.ip_address,
            "user_agent": h.user_agent,
            "login_at": h.login_at.isoformat() if h.login_at else None,
            "logout_at": h.logout_at.isoformat() if h.logout_at else None,
            "success": h.success,
            "failure_reason": h.failure_reason
        }
        for h in historial
    ]
    return respuesta_exito(resultado)


# =============================================================================
# INICIALIZACIÓN
# =============================================================================
if __name__ == "__main__":
    asegurar_admin_mbsystem()

    print("==========================================================")
    print("   Servidor de Gestión Universitaria Activo (Modo Clean)")
    print("   URL Local: http://127.0.0.1:5000")
    print("==========================================================")
    app.run(debug=True, port=5000)
