# 📚 Documentación del proyecto UniGestion PRO

## Índice
- [Visión general](#visión-general)
- [Arquitectura técnica](#arquitectura-técnica)
- [Instalación y ejecución local](#instalación-y-ejecución-local)
- [Módulo académico (Materias, Grupos, Horarios)](#módulo-académico-materias-grupos-y-horarios)
- [Endpoints HTTP (admin)](#endpoints-http-admin)
- [Modelos SQLAlchemy](#modelos-sqlalchemy)
- [Contribuir](#contribuir)
- [Licencia](#licencia)

---

### Visión general
`UniGestion PRO` es una plataforma web **Flask** que permite la gestión académica de una universidad: carreras, materias, grupos, horarios, estudiantes, docentes y procesos de cambio de grupo. Incluye seguridad robusta con **Argon2** y **JWT**.

### Arquitectura técnica
- **Backend**: Flask 3.0, SQLAlchemy 2.0 (ORM) + SQLite (dos bases de datos: `mb_system.db` y `universidad.db`).
- **Frontend**: HTML5 semántico, CSS vanilla y JavaScript ES6.
- **Despliegue**: Gunicorn + Render (CI/CD).
- **Seguridad**: Argon2‑cffi para hashing de contraseñas, JWT HS256 para tokens, bloqueo tras 3 intentos fallidos.

### Instalación y ejecución local
1. **Clonar** el repositorio:
   ```bash
   git clone https://github.com/cryshett/Gestion-Universitaria.git
   cd Gestion-Universitaria
   ```
2. **Crear entorno virtual** (PowerShell):
   ```powershell
   python -m venv .venv
   .venv\Scripts\Activate.ps1
   ```
3. **Instalar dependencias**:
   ```bash
   pip install -r requirements.txt
   ```
4. **Ejecutar**:
   ```bash
   python app.py
   ```
   Acceder a `http://127.0.0.1:5000/`.

---

## Módulo académico (Materias, Grupos, Horarios)
### Modelos SQLAlchemy
| Modelo | Campos | Descripción |
|---|---|---|
| **Materia** | `id` (PK), `codigo` (único), `nombre`, `creditos`, `carrera` | Representa una asignatura. |
| **Grupo** | `id` (PK), `codigo_grupo` (e.g., "G1"), `materia_id` (FK a Materia) | Sección de una materia. |
| **Horario** | `id` (PK), `grupo_id` (FK a Grupo), `dia`, `hora_inicio`, `hora_fin`, `aula` | Horario asociado a un grupo. |

### Rutas backend (admin)
- **Materias** – `/admin/materias`
  - `GET`: muestra formulario y tabla de materias.
  - `POST`: recibe `codigo, nombre, creditos, carrera` y guarda una nueva `Materia`.
- **Grupos** – `/admin/grupos`
  - `GET`: formulario con `<select>` de materias existentes.
  - `POST`: recibe `materia_id, codigo_grupo` y crea un `Grupo`.
- **Horarios** – `/admin/horarios`
  - `GET`: formulario con `<select>` de grupos existentes.
  - `POST`: recibe `grupo_id, dia, hora_inicio, hora_fin, aula` y crea un `Horario`.

#### Manejo de errores
```python
try:
    db.session.add(instancia)
    db.session.commit()
except Exception as e:
    db.session.rollback()
    print(f"Error al guardar: {e}")
    flash(f"Error al guardar: {e}", "danger")
```

---

## Endpoints HTTP (admin)
| Método | Ruta | Acción |
|---|---|---|
| GET | `/admin/materias` | Visualiza listado y formulario de materias |
| POST | `/admin/materias` | Crea nueva materia |
| GET | `/admin/grupos` | Formulario para crear grupos |
| POST | `/admin/grupos` | Crea nuevo grupo |
| GET | `/admin/horarios` | Formulario para crear horarios |
| POST | `/admin/horarios` | Crea nuevo horario |

---

## Contribuir
1. Fork el repositorio.
2. Crea una rama para tu feature (`git checkout -b feature/nueva-funcionalidad`).
3. Realiza los cambios y ejecuta las pruebas (`python -m pytest`).
4. Haz commit y push a tu fork.
5. Abre un Pull Request contra `main`.

---

## Licencia
Distribuido bajo la licencia **MIT**. Ver archivo `LICENSE` para más detalle.
