"""
app/db/connection.py
====================
Capa de abstracción de base de datos con soporte dual transparente para:
1. PostgreSQL (Producción en Render vía psycopg2 / DATABASE_URL)
2. SQLite (Desarrollo local / pruebas vía sqlite3)

Características:
- Reemplazo transparente de marcadores de posición ('?' -> '%s' en PostgreSQL).
- Compatibilidad total con cursores de acceso por clave ('row["col"]') y por índice ('row[0]').
- Manejo de transacciones atómicas con soporte de context manager ('with db:').
- Métodos auxiliares para introspección agnóstica de tablas y columnas (PRAGMA vs information_schema).
"""

import os
import re
import sqlite3
from typing import Any, List, Dict, Optional, Sequence, Tuple
from app.core.config import settings

# Verificamos disponibilidad de psycopg2
try:
    import psycopg2
    import psycopg2.extras
    PSYCOPG2_AVAILABLE = True
except ImportError:
    PSYCOPG2_AVAILABLE = False


class RowWrapper:
    """
    Envuelve un registro retornado por PostgreSQL (DictRow) o SQLite (Row)
    garantizando acceso dual tanto por nombre de columna como por índice numérico,
    además de permitir dict(row).
    """
    def __init__(self, data_dict: dict, data_tuple: tuple, keys: list):
        self._dict = data_dict
        self._tuple = data_tuple
        self._keys = keys

    def __getitem__(self, item):
        if isinstance(item, int):
            return self._tuple[item]
        return self._dict[item]

    def get(self, key: str, default: Any = None) -> Any:
        return self._dict.get(key, default)

    def keys(self):
        return self._dict.keys()

    def values(self):
        return self._dict.values()

    def items(self):
        return self._dict.items()

    def __iter__(self):
        return iter(self._dict)

    def __len__(self):
        return len(self._dict)

    def __repr__(self):
        return repr(self._dict)


class CursorAdapter:
    """Cursor agnóstico que adapta placeholders y normaliza filas."""
    def __init__(self, raw_cursor, is_postgres: bool):
        self.cursor = raw_cursor
        self.is_postgres = is_postgres

    def _adapt_sql(self, sql: str) -> str:
        if not self.is_postgres:
            return sql
        # En PostgreSQL los parámetros se marcan con %s en lugar de ?
        return sql.replace("?", "%s")

    def execute(self, sql: str, params: Optional[Sequence[Any]] = None):
        adapted_sql = self._adapt_sql(sql)
        if params is not None:
            if isinstance(params, list):
                params = tuple(params)
            return self.cursor.execute(adapted_sql, params)
        return self.cursor.execute(adapted_sql)

    def executemany(self, sql: str, param_list: Sequence[Sequence[Any]]):
        adapted_sql = self._adapt_sql(sql)
        return self.cursor.executemany(adapted_sql, param_list)

    def _wrap_row(self, raw_row):
        if raw_row is None:
            return None
        if not self.is_postgres:
            return raw_row  # sqlite3.Row ya soporta acceso por clave e índice
        # En PostgreSQL con DictCursor
        if hasattr(raw_row, 'keys'):
            keys = list(raw_row.keys())
            d = dict(raw_row)
            t = tuple(raw_row[k] for k in keys)
            return RowWrapper(d, t, keys)
        return raw_row

    def fetchone(self):
        row = self.cursor.fetchone()
        return self._wrap_row(row)

    def fetchall(self):
        rows = self.cursor.fetchall()
        return [self._wrap_row(r) for r in rows]

    def fetchmany(self, size: int = 1):
        rows = self.cursor.fetchmany(size)
        return [self._wrap_row(r) for r in rows]

    @property
    def description(self):
        return self.cursor.description

    @property
    def rowcount(self):
        return self.cursor.rowcount

    @property
    def lastrowid(self):
        return getattr(self.cursor, "lastrowid", None)

    def close(self):
        self.cursor.close()


class DBConnection:
    """
    Envoltura unificada para conexiones de base de datos (SQLite o PostgreSQL).
    Mantiene compatibilidad exacta con la API de sqlite3.Connection usada en Flask.
    """
    def __init__(self, is_postgres: bool, raw_conn):
        self.is_postgres = is_postgres
        self._conn = raw_conn

    def cursor(self) -> CursorAdapter:
        if self.is_postgres:
            raw_cur = self._conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        else:
            raw_cur = self._conn.cursor()
        return CursorAdapter(raw_cur, self.is_postgres)

    def execute(self, sql: str, params: Optional[Sequence[Any]] = None) -> CursorAdapter:
        cur = self.cursor()
        cur.execute(sql, params)
        return cur

    def executemany(self, sql: str, param_list: Sequence[Sequence[Any]]) -> CursorAdapter:
        cur = self.cursor()
        cur.executemany(sql, param_list)
        return cur

    def commit(self):
        self._conn.commit()

    def rollback(self):
        self._conn.rollback()

    def close(self):
        self._conn.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            self.rollback()
        else:
            self.commit()


def get_raw_connection() -> DBConnection:
    """Crea y retorna una nueva conexión unificada según settings.DATABASE_URL."""
    if settings.is_postgres:
        if not PSYCOPG2_AVAILABLE:
            raise RuntimeError(
                "psycopg2 no está instalado. Instálalo con 'pip install psycopg2-binary' para usar PostgreSQL."
            )
        # Conectar a PostgreSQL en Render
        conn = psycopg2.connect(settings.DATABASE_URL)
        return DBConnection(is_postgres=True, raw_conn=conn)
    else:
        # En desarrollo local usamos universidad.db
        conn = sqlite3.connect("universidad.db", timeout=30.0, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return DBConnection(is_postgres=False, raw_conn=conn)


def get_db_inspector_info(db: DBConnection, etiquetas_campos: Dict[str, str]) -> Dict[str, Any]:
    """
    Retorna el esquema y registros de las tablas para el visor interactivo de administración,
    soportando tanto SQLite como PostgreSQL.
    """
    cur = db.cursor()
    tablas = []

    if db.is_postgres:
        cur.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
              AND table_type = 'BASE TABLE'
            ORDER BY table_name ASC;
        """)
        tablas = [r[0] for r in cur.fetchall()]
    else:
        cur.execute("""
            SELECT name 
            FROM sqlite_master 
            WHERE type='table' AND name != 'sqlite_sequence';
        """)
        tablas = [r[0] for r in cur.fetchall()]

    resultado = {}
    for tabla in tablas:
        if tabla in ("spatial_ref_sys", "alembic_version"):
            continue

        columnas_detalle = []
        columnas = []

        if db.is_postgres:
            cur.execute("""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns 
                WHERE table_schema = 'public' AND table_name = %s
                ORDER BY ordinal_position ASC;
            """, (tabla,))
            for col in cur.fetchall():
                c_name = col["column_name"]
                columnas.append(c_name)
                columnas_detalle.append({
                    "nombre": c_name,
                    "etiqueta": etiquetas_campos.get(c_name, c_name),
                    "tipo": col["data_type"],
                    "notnull": 1 if col["is_nullable"] == "NO" else 0,
                    "pk": 1 if c_name == "id" else 0
                })
        else:
            cols_info = cur.execute(f"PRAGMA table_info({tabla});").fetchall()
            for c in cols_info:
                columnas.append(c[1])
                columnas_detalle.append({
                    "nombre": c[1],
                    "etiqueta": etiquetas_campos.get(c[1], c[1]),
                    "tipo": c[2],
                    "notnull": c[3],
                    "pk": c[5]
                })

        cur.execute(f"SELECT * FROM {tabla};")
        registros = [dict(r) for r in cur.fetchall()]

        resultado[tabla] = {
            "totalRegistros": len(registros),
            "columnas": columnas,
            "columnasDetalle": columnas_detalle,
            "muestra": registros
        }

    return resultado


def init_database_tables(db: DBConnection):
    """
    Crea y garantiza todas las tablas académicas y relacionales en la base de datos conectada
    (carreras, profesores, asignaturas, grupos, horarios, estudiantes, inscripciones, notificaciones, solicitudes).
    """
    cur = db.cursor()

    if db.is_postgres:
        # DDL PostgreSQL
        ddl_statements = [
            """
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
            """,
            """
            CREATE TABLE IF NOT EXISTS profesores (
                id VARCHAR(20) PRIMARY KEY,
                documento VARCHAR(20) UNIQUE NOT NULL,
                nombre VARCHAR(100) NOT NULL,
                primer_nombre VARCHAR(50) DEFAULT '',
                segundo_nombre VARCHAR(50) DEFAULT '',
                primer_apellido VARCHAR(50) DEFAULT '',
                segundo_apellido VARCHAR(50) DEFAULT '',
                email VARCHAR(100) UNIQUE NOT NULL,
                telefono VARCHAR(30) DEFAULT '+52 55 5555-0000',
                titulo_academico VARCHAR(100) DEFAULT 'Docente Titular',
                carrera_principal VARCHAR(10) NOT NULL,
                estado VARCHAR(20) NOT NULL DEFAULT 'Activo',
                username VARCHAR(50) DEFAULT '',
                user_id INT DEFAULT NULL
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS asignaturas (
                id VARCHAR(20) PRIMARY KEY,
                codigo VARCHAR(20) UNIQUE NOT NULL,
                nombre VARCHAR(150) NOT NULL,
                creditos INT NOT NULL,
                nivel INT NOT NULL CHECK (nivel IN (1, 2, 3)),
                tipo VARCHAR(20) NOT NULL CHECK (tipo IN ('exclusiva', 'compartida')),
                carrera_id VARCHAR(10) DEFAULT NULL,
                carreras_compartidas VARCHAR(100) DEFAULT NULL,
                docente VARCHAR(100) DEFAULT 'Por asignar',
                horario VARCHAR(50) DEFAULT 'Por definir',
                grupo VARCHAR(10) DEFAULT 'G1',
                aula VARCHAR(50) DEFAULT 'Aula 101'
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS grupos (
                id VARCHAR(30) PRIMARY KEY,
                nombre VARCHAR(20) NOT NULL,
                asignatura_id VARCHAR(20) NOT NULL,
                profesor_id VARCHAR(20) DEFAULT NULL,
                cupo_maximo INT NOT NULL DEFAULT 15,
                periodo VARCHAR(20) NOT NULL DEFAULT '2026-1',
                estado VARCHAR(20) NOT NULL DEFAULT 'Activo'
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS horarios (
                id SERIAL PRIMARY KEY,
                grupo_id VARCHAR(30) NOT NULL,
                dia_semana VARCHAR(20) NOT NULL,
                hora_inicio VARCHAR(10) NOT NULL,
                hora_fin VARCHAR(10) NOT NULL,
                aula VARCHAR(50) NOT NULL,
                edificio VARCHAR(50) DEFAULT 'Edificio Central'
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS estudiantes (
                id VARCHAR(20) PRIMARY KEY,
                matricula VARCHAR(30) UNIQUE NOT NULL,
                documento VARCHAR(20) UNIQUE,
                nombre VARCHAR(100) NOT NULL,
                primer_nombre VARCHAR(50) DEFAULT '',
                segundo_nombre VARCHAR(50) DEFAULT '',
                primer_apellido VARCHAR(50) DEFAULT '',
                segundo_apellido VARCHAR(50) DEFAULT '',
                email VARCHAR(100) NOT NULL,
                telefono VARCHAR(30) DEFAULT '+52 55 5555-5555',
                carrera_id VARCHAR(10) NOT NULL,
                semestre INT NOT NULL CHECK (semestre BETWEEN 1 AND 10),
                grupo VARCHAR(10) NOT NULL DEFAULT 'G1',
                estado VARCHAR(20) NOT NULL CHECK (estado IN ('Activo', 'En Riesgo', 'Egresado', 'Suspendido')) DEFAULT 'Activo',
                estado_pago VARCHAR(20) NOT NULL DEFAULT 'Al día' CHECK (estado_pago IN ('Al día', 'Pendiente', 'Bloqueado')),
                promedio DOUBLE PRECISION NOT NULL DEFAULT 0.0,
                foto_avatar VARCHAR(255) NOT NULL,
                username VARCHAR(50) DEFAULT '',
                user_id INT DEFAULT NULL
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS inscripciones (
                id SERIAL PRIMARY KEY,
                estudiante_id VARCHAR(20) NOT NULL,
                asignatura_id VARCHAR(20) NOT NULL,
                nota DOUBLE PRECISION NOT NULL CHECK (nota BETWEEN 0.0 AND 5.0),
                periodo VARCHAR(20) NOT NULL DEFAULT '2026-1',
                UNIQUE (estudiante_id, asignatura_id)
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS notificaciones (
                id SERIAL PRIMARY KEY,
                estudiante_id VARCHAR(20) NOT NULL,
                titulo VARCHAR(150) NOT NULL,
                mensaje TEXT NOT NULL,
                tipo VARCHAR(20) NOT NULL DEFAULT 'pago' CHECK (tipo IN ('pago', 'academico', 'sistema')),
                fecha VARCHAR(30) NOT NULL,
                leido SMALLINT NOT NULL DEFAULT 0
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS solicitudes_cambio_grupo (
                id SERIAL PRIMARY KEY,
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
            """
        ]
        for stmt in ddl_statements:
            cur.execute(stmt)
        db.commit()

    else:
        # DDL SQLite
        cur.cursor.executescript("""
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
                primer_nombre VARCHAR(50) DEFAULT '',
                segundo_nombre VARCHAR(50) DEFAULT '',
                primer_apellido VARCHAR(50) DEFAULT '',
                segundo_apellido VARCHAR(50) DEFAULT '',
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
                docente VARCHAR(100) DEFAULT 'Por asignar',
                horario VARCHAR(50) DEFAULT 'Por definir',
                grupo VARCHAR(10) DEFAULT 'G1',
                aula VARCHAR(50) DEFAULT 'Aula 101'
            );

            CREATE TABLE IF NOT EXISTS grupos (
                id VARCHAR(30) PRIMARY KEY,
                nombre VARCHAR(20) NOT NULL,
                asignatura_id VARCHAR(20) NOT NULL,
                profesor_id VARCHAR(20) DEFAULT NULL,
                cupo_maximo INT NOT NULL DEFAULT 15,
                periodo VARCHAR(20) NOT NULL DEFAULT '2026-1',
                estado VARCHAR(20) NOT NULL DEFAULT 'Activo'
            );

            CREATE TABLE IF NOT EXISTS horarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                grupo_id VARCHAR(30) NOT NULL,
                dia_semana VARCHAR(20) NOT NULL,
                hora_inicio VARCHAR(10) NOT NULL,
                hora_fin VARCHAR(10) NOT NULL,
                aula VARCHAR(50) NOT NULL,
                edificio VARCHAR(50) DEFAULT 'Edificio Central'
            );

            CREATE TABLE IF NOT EXISTS estudiantes (
                id VARCHAR(20) PRIMARY KEY,
                matricula VARCHAR(30) UNIQUE NOT NULL,
                documento VARCHAR(20) UNIQUE,
                nombre VARCHAR(100) NOT NULL,
                primer_nombre VARCHAR(50) DEFAULT '',
                segundo_nombre VARCHAR(50) DEFAULT '',
                primer_apellido VARCHAR(50) DEFAULT '',
                segundo_apellido VARCHAR(50) DEFAULT '',
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
        db.commit()

    # Sembrar carreras iniciales si la tabla está vacía
    cur.execute("SELECT COUNT(*) FROM carreras;")
    row_count = cur.fetchone()
    count = row_count[0] if row_count else 0
    if count == 0:
        carreras_base = [
            ("ISW", "Ingeniería de Software", "ISW", 8, 160, 30, "#3b82f6", "Formación integral en desarrollo y arquitectura de software.", "code"),
            ("MED", "Medicina Humana", "MED", 10, 220, 30, "#10b981", "Excelencia médica, ciencias biológicas y salud comunitaria.", "stethoscope"),
            ("DER", "Derecho y Ciencias Políticas", "DER", 8, 150, 30, "#8b5cf6", "Ciencias jurídicas, derecho civil, penal y corporativo.", "scale")
        ]
        cur.executemany("INSERT INTO carreras VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);", carreras_base)
        db.commit()
