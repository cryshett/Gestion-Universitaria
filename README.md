# 🎓 UniGestion PRO - Sistema Integral de Gestión Universitaria y Control de Acceso

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg?logo=python&logoColor=white)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-3.0.0-black.svg?logo=flask&logoColor=white)](https://flask.palletsprojects.com/)
[![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0%2B-red.svg)](https://www.sqlalchemy.org/)
[![SQLite](https://img.shields.io/badge/SQLite-3-003B57.svg?logo=sqlite&logoColor=white)](https://www.sqlite.org/)
[![Gunicorn](https://img.shields.io/badge/Gunicorn-21.2.0-green.svg?logo=gunicorn&logoColor=white)](https://gunicorn.org/)
[![Seguridad](https://img.shields.io/badge/Seguridad-Argon2%20%2B%20JWT-orange.svg)](https://cheatsheetseries.owasp.org/)

**UniGestion PRO** es una plataforma web integral orientada a la administración académica y control de acceso institucional. Integra gestión de carreras profesionales, catálogo de asignaturas exclusivas y compartidas, asignación de docentes, mallas de horarios semanales, aforo de aulas por sección, trámites de cambio de grupo con triple candado de validación, estados financieros de cobranza y un sistema de seguridad de doble base de datos con autenticación criptográfica robusta.

---

### 🌐 **Enlace Público Interactivo en Vivo (GitHub Pages)**:
👉 **[https://cryshett.github.io/Gestion-Universitaria/](https://cryshett.github.io/Gestion-Universitaria/)**

---

## 🏛️ 1. Arquitectura Técnica y Modelo de Doble Base de Datos

El sistema implementa una arquitectura desacoplada **MVC / RESTful API** basada en el principio de separación de responsabilidades, dividiendo la seguridad y auditoría de la lógica de negocio académica en dos motores de base de datos coordinados:

```text
                               ┌──────────────────────────────────────────────┐
                               │             UniGestion PRO (app.py)          │
                               │       Flask + Flask `g` Context Manager      │
                               └──────────────────────┬───────────────────────┘
                                                      │
                       ┌──────────────────────────────┴──────────────────────────────┐
                       ▼                                                             ▼
       ┌──────────────────────────────┐                              ┌──────────────────────────────┐
       │         mb_system.db         │                              │        universidad.db        │
       │       (SQLAlchemy ORM)       │                              │       (SQLite3 Nativo)       │
       ├──────────────────────────────┤                              ├──────────────────────────────┤
       │ • users (Argon2 hashes)      │                              │ • carreras (ISW, MED, DER)   │
       │ • refresh_tokens (JWT JTI)   │                              │ • profesores (DOC-001...)    │
       │ • login_history (Auditoría)  │                              │ • asignaturas (52 materias)  │
       │ • Bloqueo tras 3 fallos (5m) │                              │ • estudiantes (EST-001...)   │
       │ • Roles RBAC (admin, etc.)   │                              │ • inscripciones y notas      │
       │                              │                              │ • notificaciones financieras │
       │                              │                              │ • solicitudes_cambio_grupo   │
       └──────────────────────────────┘                              └──────────────────────────────┘
```

### A. Base de Datos de Seguridad y Control de Acceso (`mb_system.db`)
Gestionada a través de **SQLAlchemy ORM** (`app/models/` y `app/db/session.py`):
- **`users`**: Almacena `username`, `email`, `hashed_password` (encriptado con **Argon2** bajo estándares OWASP), `role` (`admin`, `teacher`, `student`, `usuario`), `is_active`, conteo de intentos fallidos (`failed_attempts`), timestamp de bloqueo (`locked_until`) y fecha de creación.
- **`refresh_tokens`**: Registro de identificadores únicos JTI de tokens de refresco para rotación segura y revocación de sesiones JWT.
- **`login_history`**: Bitácora inmutable de auditoría forense con dirección IP, User-Agent del navegador, causal exacta de rechazo (si aplica) y timestamp UTC.

### B. Base de Datos de Gestión Académica (`universidad.db`)
Gestionada con el conector optimizado de **SQLite3** y gestión de conexión por petición HTTP mediante el contexto `g` de Flask:
- **`carreras`**: Catálogo de facultades activas (`ISW` - Software, `MED` - Medicina, `DER` - Derecho) con cupo estricto de 30 plazas cada una.
- **`profesores`**: Ficha del cuerpo docente con nombres divididos, documento, título profesional, departamento y vinculación por `user_id` y `username`.
- **`asignaturas`**: Malla curricular de 52 materias (15 exclusivas por carrera + 7 transversales/compartidas), créditos, niveles formativos, horarios y docentes asignados.
- **`estudiantes`**: Directorio de alumnos matriculados con nombres divididos, documento/cédula única, matrícula automática, semestre, grupo (`G1`, `G2`), promedio ponderado, foto avatar y vinculación por `user_id` y `username`.
- **`inscripciones`**: Registro de calificaciones cursadas (0.0 a 5.0) y periodos lectivos.
- **`solicitudes_cambio_grupo`**: Trámites encolados para dictamen administrativo.
- **`notificaciones`**: Centro de alertas y avisos de cobranza / dictámenes en tiempo real.

---

## 🛠️ 2. Requisitos de Entorno y Stack Tecnológico

| Capa | Tecnología | Propósito |
|---|---|---|
| **Lenguaje** | Python 3.10 / 3.11 / 3.12 / 3.14 | Entorno de ejecución principal backend |
| **Framework Web** | Flask 3.0.0 | Servidor HTTP y orquestador de rutas API RESTful |
| **Capa ORM** | SQLAlchemy 2.0+ | Mapeo objeto-relacional y migraciones de `mb_system.db` |
| **Almacenamiento** | SQLite3 | Motor de base de datos relacional sin servidor |
| **Servidor WSGI** | Gunicorn 21.2.0 | Servidor de aplicaciones para producción (Render/Linux) |
| **Criptografía** | Argon2-cffi + Passlib | Algoritmo de derivación de claves resistente a ataques por GPU |
| **Seguridad Token** | PyJWT | Generación y verificación de tokens de acceso HS256 |
| **Validación** | Pydantic + Pydantic-Settings | Esquemas y carga segura de variables de configuración |
| **Frontend** | HTML5 Semántico + Vanilla CSS3 | Arquitectura CSS con design tokens, variables y responsive grid |
| **Interactividad** | JavaScript ES6+ Vanilla | Cliente API asíncrono, State pattern y refresco en caliente |
| **Iconografía** | Lucide Icons | Paquete visual moderno y liviano |

---

## 💻 3. Instrucciones Paso a Paso para Instalación y Ejecución Local

### Paso 1: Clonar el Repositorio
```bash
git clone https://github.com/cryshett/Gestion-Universitaria.git
cd Gestion-Universitaria
```

### Paso 2: Crear y Activar Entorno Virtual
En **Windows (PowerShell)**:
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

En **Linux / macOS**:
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### Paso 3: Instalar Dependencias
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### Paso 4: Ejecutar el Servidor Web
```bash
python app.py
```

El servidor inicializará las bases de datos `mb_system.db` y `universidad.db` automáticamente si no existen, garantizando la presencia del usuario Administrador.

Accede desde tu navegador:
👉 **[http://127.0.0.1:5000/login](http://127.0.0.1:5000/login)**

### Modo Standalone Offline (Sin Servidor Python)
Si deseas explorar la maqueta interactiva sin iniciar Flask, abre directamente en el navegador el archivo:
- [`abrir_modulo.html`](abrir_modulo.html) o [`index.html`](index.html).

---

## 🔑 4. Credenciales de Acceso por Defecto

Por diseño estricto de seguridad, la plataforma descarta cualquier cuenta demo heredada y conserva **únicamente** al Administrador Rectoral. Las cuentas de Estudiantes y Profesores se dan de alta dinámicamente desde el panel de control rectoral:

| Rol | Usuario / Identificador | Correo Institucional | Contraseña | Ruta de Acceso |
|---|---|---|---|---|
| 👑 **Administrador (Rector)** | `admin` | `admin@mbsystem.com` | `Contraseña123` | `/admin` |
| 🧑‍🏫 **Profesor / Docente** | *Auto-generado por el sistema* | `*@universidad.edu` | *Asignada al registrar* | `/teacher` |
| 🎓 **Estudiante** | *Auto-generado por el sistema* | `*@universidad.edu` | *Asignada al registrar* | `/student` |

> 🔒 **Bloqueo Automático por Fuerza Bruta**: Tras **3 intentos fallidos consecutivos** de contraseña, la cuenta entra en estado de bloqueo temporal estricto durante **5 minutos** (HTTP 423 Locked), auditando la IP y causal en la tabla `login_history`.

---

## ⚡ 5. Flujo de Creación Automática de Usuarios y Persistencia Atómica

El panel de administración incluye un formulario reestructurado con generación algorítmica de credenciales y previsualización en tiempo real:

### A. Estructura de Nombres
- **Primer Nombre** (*obligatorio*).
- **Segundo Nombre** (*opcional*).
- **Primer Apellido** (*obligatorio*).
- **Segundo Apellido** (*opcional*).
- **Número de Identificación** (*Cédula o Documento de Identidad, validado como único*).
- **Contraseña Inicial** (*mínimo 6 caracteres*).
- **Datos Académicos Dinámicos**:
  - *Estudiante*: Carrera (`ISW`, `MED`, `DER`), Semestre (1º a 8º) y Grupo (`G1`, `G2`).
  - *Profesor*: Carrera / Departamento Asignado y Grado o Título Académico.

### B. Regla Algorítmica de Generación de Username
1. Se extrae la primera letra del primer nombre normalizado.
2. Si existe segundo nombre, se extrae su primera letra normalizada.
3. Se concatena el primer apellido completo en minúsculas, sin espacios, tildes ni caracteres diacríticos (mediante descomposición Unicode `NFKD`).
4. **Ejemplos**:
   - *"Juan Carlos Pérez"* $\rightarrow$ `jcperez`
   - *"Ana Gómez"* $\rightarrow$ `agomez`
5. **Manejo de Duplicados (Colisiones)**: Si el username ya existe en `users`, el algoritmo agrega un sufijo incremental (`jcperez1`, `jcperez2`, ...) hasta asegurar disponibilidad.

### C. Regla de Generación de Correo Institucional
$$\text{email} = \text{username\_generado} + \text{"@universidad.edu"}$$
Ejemplo: `jcperez@universidad.edu`.

### D. Persistencia Atómica Dual (Two-Phase Commit Pattern)
1. Se valida la no duplicidad del número de identificación tanto en la tabla `estudiantes` como en `profesores`.
2. Se instancia el registro en SQLAlchemy (`User`) y se ejecuta `db_sqla.flush()` para obtener el `user.id`.
3. Se inserta en SQLite (`universidad.db`) en la tabla correspondiente guardando nombres divididos, identificación, vinculación con `user_id` y `username`.
4. Si SQLite concluye satisfactoriamente, se ejecuta `db_sqla.commit()`.
5. Si ocurre cualquier excepción en SQLite, se dispara un `db_sqla.rollback()`, garantizando que jamás queden usuarios huérfanos en `mb_system.db`.

---

## ☁️ 6. Guía de Despliegue en Render usando Gunicorn

El repositorio está listo para despliegue continuo (**CI/CD**) en plataformas PaaS como **Render**, **Railway** o **Fly.io**.

### Configuración en Render:
1. Conecta tu cuenta de GitHub a [Render Dashboard](https://dashboard.render.com/).
2. Selecciona **New +** $\rightarrow$ **Web Service**.
3. Elige el repositorio `cryshett/Gestion-Universitaria`.
4. Define los siguientes parámetros:
   - **Name**: `modulo-universitario-gestion` (o el nombre de tu preferencia)
   - **Region**: `Ohio (US East)` u otra cercana.
   - **Branch**: `main`
   - **Runtime**: `Python 3`
   - **Build Command**:
     ```bash
     pip install -r requirements.txt
     ```
   - **Start Command**:
     ```bash
     gunicorn app:app
     ```
5. El archivo [`Procfile`](Procfile) en la raíz del proyecto ya contiene la instrucción oficial:
   ```text
   web: gunicorn app:app
   ```
6. **Variables de Entorno (Environment Variables)**:
   - `SECRET_KEY`: `tu_clave_secreta_en_produccion_2026`
   - `PYTHON_VERSION`: `3.10.12` (o superior)
7. Haz clic en **Create Web Service**. Cada commit en `main` desplegará la versión más reciente en minutos.

---

## 📡 7. Catálogo de Endpoints RESTful API

| Método | Ruta | Descripción | Payload / Parámetros |
|---|---|---|---|
| `POST` | `/api/login` | Autenticación con Argon2 y apertura de sesión. | `{"usuario": "...", "clave": "..."}` |
| `POST` | `/api/logout` | Cierre de sesión y revocación del contexto. | `{}` |
| `GET` | `/api/me` | Datos del usuario autenticado y perfil académico. | N/A |
| `GET` | `/api/dashboard` | Métricas agregadas y estadísticas para Rectoría. | N/A |
| `GET` | `/api/carreras` | Catálogo de carreras y aforos disponibles. | N/A |
| `GET` | `/api/asignaturas` | Lista filtrable de las 52 materias curriculares. | `carrera_id`, `nivel`, `docente`, `tipo`, `q` |
| `GET` | `/api/grupos` | Secciones académicas con cupos e inscritos. | `carrera_id`, `grupo` |
| `GET` | `/api/estudiantes` | Directorio de estudiantes con filtros avanzados. | `carrera_id`, `semestre`, `estado`, `estado_pago`, `q` |
| `GET` | `/api/estudiantes/<id>` | Ficha completa y récord académico del alumno. | N/A |
| `POST` | `/api/estudiantes/<id>/notas` | Carga o actualización de nota formativa (0.0 - 5.0). | `{"asignatura_id": "...", "nota": 4.5}` |
| `POST` | `/api/estudiantes/<id>/solicitar-cambio` | Encola trámite de cambio de grupo (estado PENDIENTE). | `{"asignatura_id": "...", "nuevo_grupo": "G2", "motivo": "..."}` |
| `GET` | `/api/estudiantes/<id>/solicitudes` | Historial de solicitudes de cambio del estudiante. | N/A |
| `GET` | `/api/estudiantes/<id>/horario` | Matriz horaria semanal personalizada (Lun-Vie). | N/A |
| `GET` | `/api/estudiantes/<id>/notificaciones` | Bandeja de avisos académicos y financieros. | N/A |
| `POST` | `/api/estudiantes/<id>/estado-pago` | Actualiza estado de pago (`Al día`, `Pendiente`, `Bloqueado`). | `{"estado_pago": "...", "mensaje": "..."}` |
| `GET` | `/api/docentes/<id>/dashboard` | Panel docente con materias asignadas e inscritos. | N/A |
| `GET` | `/api/admin/usuarios` | Lista usuarios registrados con ficha académica vinculada. | N/A |
| `POST` | `/api/admin/crear-usuario` | Alta atómica de usuario con nombres divididos y auto-generación. | `{"primer_nombre": "...", "primer_apellido": "...", "identificacion": "...", ...}` |
| `PUT` | `/api/admin/usuarios/<id>` | Modifica email, rol o estado activo del usuario. | `{"email": "...", "role": "...", "is_active": true}` |
| `DELETE` | `/api/admin/usuarios/<id>` | Elimina usuario de ambas bases de datos atómicamente. | N/A |
| `GET` | `/api/admin/login-history` | Auditoría de accesos e intentos de intrusión. | N/A |
| `POST` | `/api/reset-db` | Reinicia bases de datos conservando únicamente al Administrador. | `{}` |

---

## 📏 8. Reglas de Negocio Institucionales

1. **Límite de Cupos por Carrera**: Máximo **30 estudiantes matriculados** por programa (`ISW`, `MED`, `DER`).
2. **Capacidad de Aulas por Sección**:
   - **Materias Exclusivas**: Máximo **10 estudiantes por grupo/sección**.
   - **Materias Compartidas**: Máximo **15 estudiantes por grupo/sección**.
3. **Escala de Calificaciones**: Rango de `0.0` a `5.0`. Nota mínima aprobatoria: `3.5`.
4. **Malla de Horarios**: Bloques de 2 horas estructurados de **Lunes a Viernes de 07:00 AM a 12:00 PM**.
5. **Triple Candado en Cambio de Grupo**: Se valida simultáneamente aforo libre en el grupo destino, correspondencia de nivel curricular y ausencia de colisión horaria con el resto de materias inscritas.

---

## 🧪 9. Ejecución de Pruebas Automatizadas

El proyecto incluye dos suites de pruebas automatizadas:

```bash
# Prueba 1: Verificación de nombres divididos, auto-generación de credenciales y atomicidad
python scratch/test_academic_user_creation.py

# Prueba 2: Verificación de depuración, login seguro Argon2/JWT y bloqueo de seguridad
python scratch/test_auth_integration.py
```

---

> 📜 Para conocer el historial completo de versiones, consulta el archivo **[`CHANGELOG.md`](CHANGELOG.md)**.  
> 📐 Para diagramas de clases, secuencias y casos de uso en Mermaid.js, consulta **[`DIAGRAMAS_UML.md`](DIAGRAMAS_UML.md)**.
