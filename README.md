# 🎓 UniGestion PRO - Sistema de Gestión Académica y Control de Acceso

**UniGestion PRO** es una plataforma web moderna para la administración integral universitaria. Permite gestionar carreras profesionales, pensum académico, asignación de 20 docentes oficiales, matrices de horarios semanales, aforo de aulas por sección, control de acceso basado en 3 roles y notificaciones financieras de cobranza en tiempo real.

---

### 🌐 **Enlace Público Interactivo en Vivo (GitHub Pages)**:
👉 **[https://cryshett.github.io/Gestion-Universitaria/](https://cryshett.github.io/Gestion-Universitaria/)**

---

## 🏛️ Arquitectura del Proyecto y Tecnologías

El sistema sigue una arquitectura desacoplada **MVC / RESTful API** con persistencia dual coordinada:

- **Backend / Servidor**: Python 3.10+, Flask Web Framework, SQLAlchemy ORM (MB-System), SQLite3 Database, Manejo de Contexto Flask `g` (Prevención de Memory Leaks), Seguridad Argon2-cffi y Tokens JWT (Access y Refresh tokens).
- **Frontend / Cliente**: HTML5 Semántico, Vanilla CSS3 (Design Tokens, CSS Variables, Layout Responsivo Grid/Flexbox), JavaScript ES6+ (Async/Await API Client, State Management Pattern, Micro-animaciones), Lucide Icons.
- **Bases de Datos**:
  - **`mb_system.db`** (SQLAlchemy ORM): Persistencia de seguridad con hashing Argon2, roles (`admin`, `teacher`, `student`, `usuario`), conteo de intentos fallidos, bloqueo automático temporal de cuentas, tokens de refresco (`refresh_tokens`) y registro de auditoría de sesiones (`login_history`).
  - **`universidad.db`** (SQLite): Persistencia de la gestión académica institucional (carreras profesionales, docentes asignados, asignaturas exclusivas y compartidas, estudiantes matriculados, grupos, horarios y solicitudes de cambio).

### 📁 Estructura de Directorios

```text
modulo-universitario-gestion/
│
├── app.py                      # Servidor Principal Flask, API RESTful y Controladores MB-System
├── app/                        # Módulos Core, Modelos SQLAlchemy y Esquemas de MB-System
│   ├── core/                   # Configuración y Utilidades de Seguridad (Argon2, JWT)
│   ├── db/                     # Sesión SQLAlchemy y Base Declarativa
│   ├── models/                 # Modelos de Usuario, RefreshToken y LoginHistory
│   ├── routers/                # Enrutadores REST de MB-System
│   └── schemas/                # Esquemas Pydantic de Validación
├── DIAGRAMAS_UML.md            # Diagramas Arquitectónicos UML en Mermaid.js (Clases y Casos de Uso)
├── migracion_mysql.sql         # Script Completo de Migración a MySQL (DDL + DML)
├── conexion_mysql.py           # Conector Oficial y Pool de Conexión a MySQL
├── abrir_modulo.html           # Versión Standalone Offline para Ejecución Local Sin Servidor
├── README.md                   # Documentación Oficial del Sistema
├── CHANGELOG.md                # Historial de Versiones y Registro de Cambios
│
├── templates/                  # Plantillas HTML de las Vistas Protegidas por Rol
│   ├── login.html              # Vista 1: Autenticación / Portal de Inicio de Sesión
│   ├── admin.html              # Vista 2: Dashboard Exclusivo del Administrador (Rectoría) y Auth
│   ├── teacher.html            # Vista 3: Dashboard Exclusivo del Docente
│   └── student.html            # Vista 4: Dashboard Exclusivo del Estudiante
│
└── static/                     # Recursos Estáticos Frontend
    ├── css/
    │   └── estilos.css         # Sistema de Estilos CSS Modular e Institucional
    └── js/
        └── app.js              # Controlador Principal JS, Cliente API y Gestión Dinámica
```

---

## 🔑 Credenciales Iniciales y Control de Acceso (MB-System)

La base de datos se inicializa en estado limpio conservando **exclusivamente la cuenta del Administrador Rectoral** de MB-System. Todas las demás cuentas de docentes y estudiantes se registran de forma dinámica desde el panel de control rectoral con sus datos académicos y número de identificación:

| Rol | Usuario / Correo | Contraseña Inicial | Ruta de Acceso | Componentes Exclusivos |
|---|---|---|---|---|
| 👑 **Administrador (Rector)** | `admin`<br>*(o `admin@mbsystem.com`)* | `Contraseña123` | `/admin` | Gestión de Cuentas Auth, Creación de Usuarios con Perfil Académico, Auditoría `login_history`, Inspector SQLite, Métricas Rectorales. |
| 🧑‍🏫 **Docente** | *(Registrado por Rector)* | *(Definida por Rector)* | `/teacher` | Dashboard de Cátedra, Horario Docente Semanal, Nómina de Alumnos y Carga de Calificaciones. |
| 🎓 **Estudiante** | *(Registrado por Rector)* | *(Definida por Rector)* | `/student` | Horario Individual, Récord Académico (Kardex), Solicitud de Cambio de Grupo y Avisos Financieros. |

> 🔒 **Seguridad Avanzada**: Tras **3 intentos fallidos consecutivos** de contraseña, la cuenta se bloquea automáticamente por 5 minutos y se audita el motivo exacto, IP y User-Agent en `login_history`.

---

## 🚀 Instrucciones de Instalación y Ejecución

### 1. Requisitos Previos
- Python 3.10 o superior instalado en el sistema.
- Flask instalado (`pip install flask`).

### 2. Ejecutar el Servidor Web
Abre una terminal en la carpeta del proyecto y ejecuta:

```bash
python app.py
```

El servidor iniciará en el puerto local **5000**:
👉 **[http://127.0.0.1:5000/login](http://127.0.0.1:5000/login)**

### 3. Modo Standalone Offline (Sin Servidor Python)
Si no deseas ejecutar el servidor Flask, puedes abrir directamente el archivo [`abrir_modulo.html`](file:///C:/Users/crist/.gemini/antigravity-ide/scratch/modulo-universitario-gestion/abrir_modulo.html) en cualquier navegador web moderno para probar la interfaz interactiva.

---

## 📡 Catálogo de Endpoints REST API

| Método HTTP | Endpoint | Descripción | Parámetros / Body |
|---|---|---|---|
| `POST` | `/api/login` | Autentica usuario y genera la sesión. | `{"usuario": "...", "clave": "..."}` |
| `GET` | `/api/me` | Retorna los datos del usuario autenticado en sesión. | N/A |
| `GET` | `/api/dashboard` | Retorna estadísticas generales del sistema. | N/A |
| `GET` | `/api/carreras` | Obtiene el catálogo de las 3 carreras activas. | N/A |
| `GET` | `/api/asignaturas` | Retorna las 52 asignaturas filtradas. | `carrera_id`, `nivel`, `docente`, `tipo`, `q` |
| `GET` | `/api/grupos` | Retorna secciones con aforo e inscritos. | `carrera_id`, `grupo` |
| `GET` | `/api/estudiantes` | Retorna directorio de estudiantes filtrado. | `carrera_id`, `semestre`, `estado`, `estado_pago`, `q` |
| `GET` | `/api/estudiantes/<id>` | Obtiene expediente y kardex del estudiante. | N/A |
| `POST` | `/api/estudiantes` | Registra un nuevo estudiante. | `{"nombre": "...", "carrera_id": "...", ...}` |
| `POST` | `/api/estudiantes/<id>/notas` | Registra/modifica nota de asignatura. | `{"asignatura_id": "...", "nota": 4.5}` |
| `POST` | `/api/estudiantes/<id>/solicitar-cambio` | Encola solicitud con estado PENDIENTE (sin cambio directo). | `{"asignatura_id": "...", "nuevo_grupo": "G2", "motivo": "..."}` |
| `GET` | `/api/estudiantes/<id>/solicitudes` | Retorna el historial de solicitudes de trámite del alumno. | N/A |
| `GET` | `/api/admin/solicitudes-cambio` | Panel Admin: Lista todas las solicitudes y conteo pendiente. | N/A |
| `POST` | `/api/admin/solicitudes-cambio/<id>/aprobar` | Admin: Aprueba solicitud, reasigna en BD y notifica al alumno. | `{}` |
| `POST` | `/api/admin/solicitudes-cambio/<id>/rechazar` | Admin: Rechaza solicitud sin alterar grupo y notifica al alumno. | `{"motivo": "..."}` |
| `GET` | `/api/estudiantes/<id>/horario` | Retorna matriz semanal individual del alumno. | N/A |
| `GET` | `/api/estudiantes/<id>/notificaciones` | Obtiene el centro de avisos y notificaciones de dictamen. | N/A |
| `POST` | `/api/estudiantes/<id>/estado-pago` | Modifica estado financiero y envía alerta. | `{"estado_pago": "Pendiente", "mensaje": "..."}` |
| `POST` | `/api/notificaciones/<id>/leida` | Marca notificación como leída. | N/A |
| `GET` | `/api/docentes/<id>/dashboard` | Panel docente con materias e inscritos. | N/A |
| `GET` | `/api/admin/usuarios` | Admin: Lista usuarios registrados con perfil académico vinculado. | N/A |
| `POST` | `/api/admin/crear-usuario` | Admin: Registra cuenta (mb_system.db) y ficha académica (universidad.db) de forma atómica. | `{"username": "...", "email": "...", "password": "...", "role": "...", "nombre": "...", "identificacion": "...", ...}` |
| `PUT` | `/api/admin/usuarios/<id>` | Admin: Modifica email, rol, estado activo o contraseña del usuario. | `{"email": "...", "role": "...", "is_active": true, ...}` |
| `DELETE` | `/api/admin/usuarios/<id>` | Admin: Elimina usuario y sus registros académicos vinculados. | N/A |
| `GET` | `/api/admin/login-history` | Admin: Retorna registro de auditoría de inicios de sesión y bloqueos. | N/A |
| `POST` | `/api/reset-db` | Admin: Restablece la base de datos conservando únicamente al Administrador MBSystem. | `{}` |


---

## 📏 Reglas de Negocio Institucionales

1. **Carreras Profesionales**: Exactamente 3 carreras activas (`ISW`, `MED`, `DER`) con límite máximo de **30 estudiantes por carrera**.
2. **Catálogo Académico**: 52 asignaturas totales (15 exclusivas por carrera + 7 compartidas/generales).
3. **Niveles Curriculares**:
   - **Nivel 1 (Fundamentos)**: 1º y 2º Semestre.
   - **Nivel 2 (Intermedio)**: 3º a 5º Semestre.
   - **Nivel 3 (Avanzado)**: 6º a 8º Semestre.
4. **Capacidad de Aulas por Sección**:
   - **Materias Exclusivas**: Máximo **10 estudiantes por grupo/sección**.
   - **Materias Compartidas**: Máximo **15 estudiantes por grupo/sección**.
5. **Horarios de Clase**: Organizados de **Lunes a Viernes de 07:00 AM a 12:00 PM** en bloques de 2 horas.
6. **Validación Automática de Cambio de Grupo**: Verifica aforo libre, restricción de nivel curricular y no traslape de horarios.

---


> 📜 Consulta la historia detallada de cada versión en el archivo **[`CHANGELOG.md`](CHANGELOG.md)**.

---

## 🐬 Guía de Migración de Base de Datos: SQLite a MySQL

El proyecto incluye el script ejecutable **[`migracion_mysql.sql`](migracion_mysql.sql)** que migra completamente el esquema relacional y todos los datos del sistema a un servidor **MySQL 5.7+ / 8.0+** o **MariaDB**.

### 1. Ejecutar el Script en MySQL
Abre tu consola de MySQL Workbench, phpMyAdmin o terminal de MySQL y ejecuta:

```bash
mysql -u root -p < migracion_mysql.sql
```

Esto creará automáticamente la base de datos `universidad_db` con las 6 tablas relacionales (`carreras`, `profesores`, `asignaturas`, `estudiantes`, `inscripciones`, `notificaciones`), claves primarias, claves foráneas y todos los registros iniciales sembrados.

### 2. Conectar Flask a MySQL (Opcional)
Para conectar la aplicación a tu servidor MySQL:

1. Instala el conector de MySQL para Python:
   ```bash
   pip install mysql-connector-python
   ```
2. Importa y utiliza el conector [`conexion_mysql.py`](conexion_mysql.py) en `app.py`:
   ```python
   from conexion_mysql import obtener_conexion_mysql
   ```


