# Documentación Arquitectónica y Diagramas UML

Este documento consolida la arquitectura técnica, modelo de datos y diseño del comportamiento del **Sistema de Gestión Universitaria (UniGestion PRO)** mediante diagramas estandarizados en formato **Mermaid.js**, renderizables directamente en GitHub, GitLab y VS Code (Markdown Preview).

---

## 1. Diagrama de Clases (Estructural)

Representa la jerarquía de entidades, atributos esenciales, métodos de negocio y relaciones estructurales (herencia, agregación, composición y asociaciones 1:N y N:M) basadas en `app.py`, `base_datos.py` y el esquema SQL.

```mermaid
classDiagram
    direction TB

    %% Jerarquía de Autenticación y Usuarios
    class Usuario {
        +String id
        +String username
        +String email
        +String password_hash
        +String rol
        +autenticar(password) bool
        +cerrarSesion() void
        +cambiarPassword(nueva_pass) bool
    }

    class Admin {
        +String nivel_acceso
        +String departamento
        +crearEstudiante(datos) Estudiante
        +actualizarEstadoPago(est_id, estado) void
        +asignarDocente(grupo_id, docente_id) void
        +gestionarGrupos(asg_id, aula, cupo) Grupo
        +restablecerBaseDatos() bool
    }

    class Docente {
        +String codigo_docente
        +String especialidad
        +String cubiculo
        +consultarGruposAsignados() List~Grupo~
        +obtenerNominaAlumnos(grupo_id) List~Estudiante~
        +registrarCalificacion(est_id, asg_id, nota) bool
        +consultarHorarioDocente() List~Horario~
    }

    class Estudiante {
        +String matricula
        +String carrera_id
        +int semestre
        +String estado
        +String estado_pago
        +float promedio
        +consultarHorarioIndividual() List~Horario~
        +consultarRecordAcademico() List~Calificacion~
        +solicitarCambioGrupo(asg_id, grupo_destino) bool
        +consultarNotificaciones() List~Notificacion~
    }

    %% Estructura Curricular y Académica
    class Carrera {
        +String id
        +String codigo
        +String nombre
        +String facultad
        +int semestres_totales
        +int cupos_maximos
        +calcularPromedioCarrera() float
    }

    class Asignatura {
        +String id
        +String codigo
        +String nombre
        +String carrera_id
        +int nivel
        +String tipo
        +int creditos
        +obtenerGruposDisponibles() List~Grupo~
    }

    class Grupo {
        +String id
        +String codigo
        +String asignatura_id
        +String docente_id
        +String aula
        +int cupo_maximo
        +int cupo_actual
        +verificarAforo() bool
        +inscribirEstudiante(est_id) bool
        +removerEstudiante(est_id) bool
    }

    class Horario {
        +String id
        +String grupo_id
        +String dia
        +String hora_inicio
        +String hora_fin
        +String bloque
        +validarTraslape(otro_horario) bool
    }

    class Calificacion {
        +String id
        +String estudiante_id
        +String asignatura_id
        +float nota
        +String estado
        +validarAprobacion() bool
    }

    class Notificacion {
        +String id
        +String estudiante_id
        +String titulo
        +String mensaje
        +String tipo
        +bool leido
        +DateTime fecha
        +marcarComoLeida() void
    }

    %% Relaciones de Herencia
    Usuario <|-- Admin : Especializa
    Usuario <|-- Docente : Especializa
    Usuario <|-- Estudiante : Especializa

    %% Relaciones de Dominio y Negocio
    Carrera "1" --> "0..*" Estudiante : matricula
    Carrera "1" --> "1..*" Asignatura : plan de estudios
    Asignatura "1" --> "1..*" Grupo : se oferta en
    Docente "1" --> "0..*" Grupo : imparte
    Grupo "1" *-- "1..*" Horario : sesiona en
    Estudiante "1" --> "0..*" Calificacion : historial de
    Asignatura "1" --> "0..*" Calificacion : corresponde a
    Estudiante "1" --> "0..*" Notificacion : recibe
    Estudiante "0..*" ..> "1..*" Grupo : inscrito mediante matrícula
```

### Detalle de Relaciones del Modelo

| Relación | Tipo | Cardinalidad | Descripción de Negocio |
|---|:---:|:---:|---|
| **Usuario $\rightarrow$ Admin / Docente / Estudiante** | Herencia | `1:1` | Generalización del sistema de autenticación con RBAC (*Role-Based Access Control*). |
| **Carrera $\rightarrow$ Estudiante** | Asociación | `1:N` | Cada alumno pertenece a un programa de pregrado (`ISW`, `MED`, `DER`). |
| **Carrera $\rightarrow$ Asignatura** | Composición | `1:N` | Malla curricular estructurada por niveles (1 al 8). |
| **Asignatura $\rightarrow$ Grupo** | Asociación | `1:N` | Cada asignatura se divide en secciones (`G1`, `G2`). |
| **Docente $\rightarrow$ Grupo** | Asociación | `1:N` | Asignación de carga académica por cátedra. |
| **Grupo $\rightarrow$ Horario** | Composición | `1:N` | Bloques semanales (ej. Lun-Mié 07:00-09:00) con control de no superposición. |
| **Estudiante $\rightarrow$ Calificación** | Asociación | `1:N` | Récord académico ponderado (escala 0.0 - 5.0). |
| **Grupo $\leftrightarrow$ Estudiante** | Asociación N:M | `N:M` | Control estricto de aforo: máximo **15 estudiantes por aula**. |

---

## 2. Diagrama de Casos de Uso (Comportamiento)

Muestra los casos de uso agrupados por el límite del sistema (*System Boundary*), destacando los tres actores principales: **Administrador**, **Docente** y **Estudiante**, junto con sus relaciones de inclusión (`<<include>>`) y extensión (`<<extend>>`).

```mermaid
flowchart LR
    %% Definición de Actores
    subgraph Actores [" Actores del Sistema "]
        Admin["fa:fa-user-shield Administrador\n(Rectoría / Control)"]
        Docente["fa:fa-chalkboard-teacher Docente\n(Profesor Catedrático)"]
        Estudiante["fa:fa-user-graduate Estudiante\n(Alumno Matriculado)"]
    end

    %% Límite del Sistema
    subgraph Sistema [" Sistema Universitario UniGestion PRO "]
        direction TB

        %% Módulo de Seguridad
        subgraph Autenticacion [" Módulo de Autenticación y Seguridad "]
            UC_Login(["Iniciar Sesión Multirrol"]):::security
            UC_Logout(["Cerrar Sesión"]):::security
            UC_ValidarCredenciales(["Validar Hash de Contraseña"]):::subroutine
        end

        %% Casos de Uso del Administrador
        subgraph ModuloAdmin [" Módulo Rectoral y Administrativo "]
            UC_GestionUsuarios(["Gestionar Alumnos y Matrícula"]):::admin
            UC_ControlFinanciero(["Control de Estados de Pago"]):::admin
            UC_AsignarCarga(["Asignar Carga Académica a Docentes"]):::admin
            UC_GestionGrupos(["Gestionar Grupos y Capacidad de Aulas"]):::admin
            UC_AlertasCobranza(["Generar Alertas de Cobranza"]):::admin
            UC_ResetBD(["Restablecer Base de Datos Demo"]):::admin
        end

        %% Casos de Uso del Docente
        subgraph ModuloDocente [" Módulo Docente "]
            UC_ConsultarCarga(["Consultar Asignaturas y Horario Docente"]):::teacher
            UC_VerLista(["Ver Nómina y Lista de Alumnos por Grupo"]):::teacher
            UC_RegistrarNotas(["Registrar y Modificar Calificaciones"]):::teacher
            UC_ExportarAsistencia(["Exportar Registro de Asistencia"]):::teacher
        end

        %% Casos de Uso del Estudiante
        subgraph ModuloEstudiante [" Módulo del Estudiante "]
            UC_ConsultarHorario(["Consultar Horario Semanal Individual"]):::student
            UC_ConsultarKardex(["Consultar Récord de Calificaciones"]):::student
            UC_CambiarGrupo(["Solicitar Cambio de Grupo de Clase"]):::student
            UC_VerNotificaciones(["Ver Notificaciones y Avisos de Cobranza"]):::student
            UC_ValidarAforo(["Validar Aforo Máx. 15 y No Traslape"]):::subroutine
        end
    end

    %% Conexiones del Administrador
    Admin --> UC_Login
    Admin --> UC_Logout
    Admin --> UC_GestionUsuarios
    Admin --> UC_ControlFinanciero
    Admin --> UC_AsignarCarga
    Admin --> UC_GestionGrupos
    Admin --> UC_ResetBD

    %% Conexiones del Docente
    Docente --> UC_Login
    Docente --> UC_Logout
    Docente --> UC_ConsultarCarga
    Docente --> UC_VerLista
    Docente --> UC_RegistrarNotas
    Docente --> UC_ExportarAsistencia

    %% Conexiones del Estudiante
    Estudiante --> UC_Login
    Estudiante --> UC_Logout
    Estudiante --> UC_ConsultarHorario
    Estudiante --> UC_ConsultarKardex
    Estudiante --> UC_CambiarGrupo
    Estudiante --> UC_VerNotificaciones

    %% Relaciones <<include>> y <<extend>>
    UC_Login -.->|<<include>>| UC_ValidarCredenciales
    UC_ControlFinanciero -.->|<<extend>>| UC_AlertasCobranza
    UC_CambiarGrupo -.->|<<include>>| UC_ValidarAforo

    %% Estilos de los Nodos
    classDef security fill:#1e293b,stroke:#0ea5e9,stroke-width:2px,color:#f8fafc;
    classDef admin fill:#eff6ff,stroke:#1e40af,stroke-width:2px,color:#1e3a8a;
    classDef teacher fill:#f0fdf4,stroke:#15803d,stroke-width:2px,color:#14532d;
    classDef student fill:#faf5ff,stroke:#7e22ce,stroke-width:2px,color:#581c87;
    classDef subroutine fill:#fffbeb,stroke:#b45309,stroke-width:1.5px,stroke-dasharray: 4 4,color:#78350f;
```

---

## 3. Matriz de Permisos y Casos de Uso por Rol

| Módulo / Caso de Uso | Administrador | Docente | Estudiante | Regla de Negocio / Restricción |
|---|:---:|:---:|:---:|---|
| **Iniciar / Cerrar Sesión** | SI | SI | SI | Autenticación con SHA-256 o bcrypt. |
| **Filtrado y Búsqueda de Estudiantes** | SI | NO | NO | Búsqueda multicriterio (carrera, semestre, estado, pago). |
| **Control Financiero (Al día / Pendiente / Bloqueado)** | SI | NO | NO | Activa o desactiva banners de cobranza institucional. |
| **Asignación de Aulas y Docentes** | SI | NO | NO | Validación de cruces horarios en aulas físicas. |
| **Consulta de Horario Semanal** | SI | SI (Cátedra) | SI (Cursado) | Matriz gráfica Lun-Vie por franjas de 2 horas. |
| **Nómina y Asistencia de Clase** | SI | SI | NO | Límite físico: máximo 15 alumnos por aula. |
| **Registro y Carga de Notas** | SI | SI | NO | Rango válido: 0.0 a 5.0. Aprobación $\ge 3.0$. |
| **Historial y Récord de Notas (Kardex)** | SI | NO | SI | Visualización de asignaturas aprobadas y promedio acumulado. |
| **Cambio de Grupo de Clase** | NO | NO | SI | **Validación de triple candado**: aforo disponible, nivel correlativo y sin colisión horaria. |
| **Bandeja de Notificaciones** | NO | NO | SI | Avisos administrativos y alertas financieras en tiempo real. |

---

## 4. Diagrama de Secuencia: Validación de Cambio de Grupo

Ilustra la interacción dinámica entre componentes cuando un estudiante solicita cambio de grupo:

```mermaid
sequenceDiagram
    autonumber
    actor E as Estudiante
    participant UI as Interfaz Web (SPA)
    participant C as Controlador (app.py)
    participant BD as Base de Datos (MySQL / SQLite)

    E->>UI: Selecciona Asignatura e indica Grupo Destino (G2)
    UI->>C: POST /api/estudiante/cambiar-grupo {est_id, asg_id, grupo_destino}
    activate C

    C->>BD: SELECT COUNT(*) FROM matricula WHERE grupo_id = 'G2'
    BD-->>C: Retorna inscritos actuales (ej: 14)

    alt Cupo Excedido (>= 15 alumnos)
        C-->>UI: 400 Bad Request: "Aforo completo en grupo destino"
        UI-->>E: Muestra notificación de advertencia
    else Cupo Disponible (< 15 alumnos)
        C->>BD: SELECT horario FROM grupos WHERE id = 'G2'
        BD-->>C: Horario del nuevo grupo

        C->>C: Validar no colisión horaria con el resto de asignaturas cursadas

        alt Existe Colisión Horaria
            C-->>UI: 400 Bad Request: "El horario seleccionado coincide con otra clase"
            UI-->>E: Alerta de conflicto de horario
        else Validación Exitosa
            C->>BD: UPDATE matricula SET grupo_id = 'G2' WHERE est_id = ...
            BD-->>C: Confirmación OK
            C-->>UI: 200 OK: "Solicitud aprobada y procesada con éxito"
            UI-->>E: Renderiza nuevo horario actualizado en pantalla
        end
    end
    deactivate C
```
