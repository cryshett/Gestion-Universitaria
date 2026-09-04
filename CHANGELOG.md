# 📜 Historial de Versiones y Registro de Cambios (CHANGELOG)

Todas las modificaciones notables del proyecto **UniGestion PRO** están documentadas en este archivo estructurado bajo el estándar de [Semantic Versioning (SemVer)](https://semver.org/lang/es/).

---

## 🛡️ [v2.2.0] - 2026-09-04 (Autenticación MB-System y Registro Académico Atómico)
### Añadido
- **Integración de Autenticación MB-System**:
  - Implementación de hashing criptográfico con **Argon2** y generación de tokens de acceso y refresco con **PyJWT**.
  - Registro de auditoría exhaustiva en la tabla `login_history` (IP, User-Agent, éxito/fallo y causal de error).
  - Bloqueo temporal automático de cuentas por 5 minutos tras 3 intentos fallidos consecutivos de contraseña.
  - Depuración completa de usuarios demo heredados, conservando exclusivamente la cuenta del Administrador Rectoral (`admin` / `admin@mbsystem.com`).
- **Ampliación de Registro de Usuarios con Datos Académicos**:
  - Formulario dinámico e interactivo en el panel rectoral para capturar Nombre Completo y Cédula/Documento común.
  - Alternancia dinámica según el rol seleccionado:
    - **Estudiante**: Selección de Carrera (`ISW`, `MED`, `DER`), Semestre curricular (1º a 8º) y Grupo académico (`G1`, `G2`).
    - **Docente**: Selección de Carrera / Departamento asignado y Título/Grado académico.
  - **Validación de Unicidad**: Control previo de duplicidad de número de identificación en estudiantes y profesores.
  - **Persistencia Dual Atómica**: Creación coordinada entre `mb_system.db` (`users`) y `universidad.db` (`estudiantes`/`profesores`) con mecanismo de rollback bidireccional ante fallos.
  - Enriquecimiento del endpoint `/api/me` y visualización de perfiles académicos vinculados en la tabla de usuarios del Administrador.

---

## 🚀 [v2.1.0] - 2026-09-03 (Fase Final & Documentación Completa)
### Añadido
- Módulo completo de **Notificaciones y Estado Financiero** de estudiantes (`Al día`, `Pendiente`, `Bloqueado`).
- Centro de notificaciones con distintivo flotante y contador de avisos no leídos en el portal del estudiante.
- Banner de advertencia de cobranza para estudiantes con saldos pendientes o cuentas bloqueadas.
- Selector de estado financiero y emisión de avisos de cobro personalizados en la vista del Administrador.
- Documentación técnica exhaustiva [`README.md`](README.md) y [`CHANGELOG.md`](CHANGELOG.md).

---

## 🔒 [v2.0.0] - 2026-09-03 (Restructuración Arquitectónica: Autenticación y 3 Roles)
### Añadido
- Sistema de autenticación basado en sesiones HTTP y control de acceso (**RBAC**).
- 4 vistas dedicadas y protegidas por servidor:
  - `/login`: Vista inicial de inicio de sesión con botones demo de acceso rápido.
  - `/admin`: Dashboard ejecutivo para el Administrador (Rectoría).
  - `/teacher`: Portal exclusivo para el claustro docente (mis clases, horarios e ingreso de notas).
  - `/student`: Portal exclusivo para estudiantes (mi horario individual, notas y cambio de grupo).
- Redirección automática de seguridad en la ruta raíz `/` según la sesión activa.

---

## 🗓️ [v1.3.0] - 2026-09-03 (Módulo de Horarios Individuales y Detalle de Grupo)
### Añadido
- Vista de **Horario Semanal Individual Grid** dentro del perfil de cada estudiante (Lunes a Viernes de 07:00 AM a 12:00 PM).
- Ventana modal de **Nómina de Alumnos** inscritos por asignatura y grupo (`G1`/`G2`).
- Restructuración del catálogo a **52 asignaturas** (15 exclusivas por carrera + 7 compartidas/generales).
- Regla de capacidad diferenciada: **10 alumnos máx** para materias exclusivas y **15 alumnos máx** para materias compartidas.

---

## 🎨 [v1.2.0] - 2026-09-03 (Optimización de UI y Navegación Sticky)
### Añadido
- Menú lateral (*Sidebar*) fijo con desplazamiento suave (`position: sticky`).
- Alternador de vistas para grupos: **Vista Tarjetas Compactas** y **Vista Lista Detallada (Tabla)**.
- Rediseño compacto de la sección **Estudiantes en Riesgo** en formato Grid responsivo de 2-4 columnas.

---

## 🏫 [v1.1.0] - 2026-09-03 (Pensum Institucional, 20 Docentes y Aforos)
### Añadido
- Incorporación de los **3 programas académicos activos**: Ingeniería de Software (`ISW`), Medicina Humana (`MED`) y Derecho (`DER`).
- Asignación oficial de **20 profesores universitarios**.
- Matriz general de horarios institucionales por bloques de 2 horas.
- Límite máximo de **30 estudiantes matriculados por carrera**.

---

## ⚙️ [v1.0.0] - 2026-09-03 (Versión Inicial / Baseline MVP)
### Añadido
- Servidor web Python Flask con API RESTful.
- Base de datos relacional SQLite (`universidad.db`) y script de generación (`base_datos.py`).
- Dashboard general con gráficos dinámicos SVG (Donut chart & Barras).
- Visor e inspector interactivo de tablas SQLite con formulario rectoral de inserción.
- Versión standalone offline [`abrir_modulo.html`](abrir_modulo.html).
