/**
 * app.js
 * ======
 * Lógica Frontend Institucional con Menú Lateral Desplegable,
 * Gráfico SVG Donut de Distribución/Cupos, Matriz de Horarios (7am-12pm)
 * y Gestión Dinámica de la Base de Datos SQLite.
 */

// =============================================================================
// 1. CAPA CLIENTE DE API (API CLIENT)
// =============================================================================
const API = {
    async request(url, options = {}) {
        try {
            const respuesta = await fetch(url, {
                headers: { 'Content-Type': 'application/json', ...options.headers },
                ...options
            });
            let data = {};
            try {
                data = await respuesta.json();
            } catch (_) {
                data = {};
            }
            if (!respuesta.ok) {
                const mensajeError = data.mensaje || (typeof data.error === 'string' ? data.error : null) || `Error HTTP ${respuesta.status}`;
                throw new Error(mensajeError);
            }
            return data;
        } catch (err) {
            UI.mostrarToast(err.message || 'Error en la comunicación con el servidor', 'danger');
            throw err;
        }
    },

    getDashboard() { return this.request('/api/dashboard'); },
    getCarreras() { return this.request('/api/carreras'); },
    getGrupos(params = {}) {
        const query = new URLSearchParams(params).toString();
        return this.request(`/api/grupos${query ? '?' + query : ''}`);
    },
    getAsignaturas(params = {}) {
        const query = new URLSearchParams(params).toString();
        return this.request(`/api/asignaturas${query ? '?' + query : ''}`);
    },
    getEstudiantes(params = {}) {
        const query = new URLSearchParams(params).toString();
        return this.request(`/api/estudiantes${query ? '?' + query : ''}`);
    },
    getDetalleEstudiante(id) { return this.request(`/api/estudiantes/${id}`); },
    crearEstudiante(payload) {
        return this.request('/api/estudiantes', { method: 'POST', body: JSON.stringify(payload) });
    },
    guardarNota(estudianteId, payload) {
        return this.request(`/api/estudiantes/${estudianteId}/notas`, { method: 'POST', body: JSON.stringify(payload) });
    },
    cambiarGrupo(estudianteId, payload) {
        return this.request(`/api/estudiantes/${estudianteId}/cambiar-grupo`, { method: 'POST', body: JSON.stringify(payload) });
    },
    getHorarioEstudiante(estudianteId) {
        return this.request(`/api/estudiantes/${estudianteId}/horario`);
    },
    getEstudiantesGrupo(asignaturaId, grupo = '') {
        return this.request(`/api/grupos/${asignaturaId}/estudiantes?grupo=${encodeURIComponent(grupo)}`);
    },
    cambiarEstadoPago(estudianteId, payload) {
        return this.request(`/api/estudiantes/${estudianteId}/estado-pago`, { method: 'POST', body: JSON.stringify(payload) });
    },
    getSolicitudesAdmin() {
        return this.request('/api/admin/solicitudes-cambio');
    },
    aprobarSolicitud(id) {
        return this.request(`/api/admin/solicitudes-cambio/${id}/aprobar`, { method: 'POST', body: JSON.stringify({}) });
    },
    rechazarSolicitud(id, motivo = '') {
        return this.request(`/api/admin/solicitudes-cambio/${id}/rechazar`, { method: 'POST', body: JSON.stringify({ motivo }) });
    },
    resetBD() { return this.request('/api/reset-db', { method: 'POST' }); },
    getDatabaseInfo() { return this.request('/api/database/tablas'); },
    insertarRegistroBD(tabla, registro) {
        return this.request('/api/database/insertar', {
            method: 'POST',
            body: JSON.stringify({ tabla, registro })
        });
    },
    getAuthUsers() { return this.request('/api/admin/usuarios'); },
    crearAuthUser(payload) {
        return this.request('/api/admin/crear-usuario', {
            method: 'POST',
            body: JSON.stringify(payload)
        });
    },
    eliminarAuthUser(id) {
        return this.request(`/api/admin/usuarios/${id}`, { method: 'DELETE' });
    },
    getAuthLoginHistory() { return this.request('/api/admin/login-history'); }
};

// =============================================================================
// 2. ESTADO REUTILIZABLE (STATE)
// =============================================================================
const State = {
    vistaActual: 'vista-dashboard',
    modoVista: 'grid',
    modoVistaGrupos: 'grid',
    filtroNivel: '',
    filtroEstadoPago: '',
    filtroSolicitud: 'TODAS',
    solicitudesCache: [],
    estudianteKardexId: null,
    dbCache: null,
    tablasAbiertas: new Set(['estudiantes'])
};


// =============================================================================
// 3. CAPA DE INTERFAZ DE USUARIO (UI)
// =============================================================================
const UI = {
    mostrarToast(mensaje, tipo = 'info') {
        let container = document.getElementById('toast-container');
        if (!container) {
            container = document.createElement('div');
            container.id = 'toast-container';
            container.className = 'toast-container';
            document.body.appendChild(container);
        }

        const toast = document.createElement('div');
        toast.className = `toast toast-${tipo}`;
        toast.innerHTML = `<span>${mensaje}</span>`;

        container.appendChild(toast);
        setTimeout(() => {
            toast.classList.add('toast-fade-out');
            setTimeout(() => toast.remove(), 300);
        }, 3500);
    },

    refrescarIconos() {
        if (window.lucide) lucide.createIcons();
    },

    renderKPICard(id, valor) {
        const el = document.getElementById(id);
        if (el) el.innerText = valor;
    },

    generarAvatarFlatUI(nombre, id, tamano = 40) {
        const paleta = [
            { bg: '#dbeafe', stroke: '#1e40af' }, // Azul
            { bg: '#ede9fe', stroke: '#5b21b6' }, // Púrpura
            { bg: '#d1fae5', stroke: '#065f46' }, // Esmeralda
            { bg: '#fef3c7', stroke: '#92400e' }, // Ámbar
            { bg: '#fee2e2', stroke: '#991b1b' }, // Carmesí
            { bg: '#e0e7ff', stroke: '#3730a3' }, // Índigo
            { bg: '#ccfbf1', stroke: '#115e59' }, // Turquesa
            { bg: '#fae8ff', stroke: '#86198f' }  // Magenta
        ];
        let hash = 0;
        const str = (id || '') + (nombre || '');
        for (let i = 0; i < str.length; i++) hash = str.charCodeAt(i) + ((hash << 5) - hash);
        const c = paleta[Math.abs(hash) % paleta.length];
        const iconSize = Math.max(14, Math.round(tamano * 0.55));
        
        return `
            <div class="student-avatar-vector" style="width:${tamano}px; height:${tamano}px; min-width:${tamano}px; min-height:${tamano}px; border-radius:50%; background:${c.bg}; border:1.5px solid ${c.stroke}; display:flex; align-items:center; justify-content:center; flex-shrink:0;" title="${nombre}">
                <svg width="${iconSize}" height="${iconSize}" viewBox="0 0 24 24" fill="none" stroke="${c.stroke}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2"></path>
                    <circle cx="12" cy="7" r="4"></circle>
                </svg>
            </div>
        `;
    },

    renderStudentCard(est) {
        const esRiesgo = est.estado === 'En Riesgo';
        const badgeClase = est.estado === 'Activo' ? 'badge-activo' : (esRiesgo ? 'badge-riesgo' : 'badge-egresado');
        const colorPromedio = est.promedio < 3.5 ? '#b91c1c' : '#047857';

        const pagoBadgeStyle = est.estado_pago === 'Bloqueado' 
            ? 'background:#fee2e2; color:#991b1b; border:1px solid #fca5a5;'
            : (est.estado_pago === 'Pendiente' ? 'background:#fef3c7; color:#92400e; border:1px solid #fde68a;' : 'background:#dcfce7; color:#166534; border:1px solid #86efac;');

        return `
            <article class="student-card" data-id="${est.id}">
                <div class="student-card-header">
                    ${UI.generarAvatarFlatUI(est.nombre, est.id, 40)}
                    <div class="student-info">
                        <h4>${est.nombre}</h4>
                        <div class="student-matricula"><code>${est.matricula}</code></div>
                        <div style="margin-top:0.25rem; display:flex; gap:0.3rem; flex-wrap:wrap;">
                            <span class="badge ${badgeClase}">${est.estado}</span>
                            <span class="badge" style="${pagoBadgeStyle}">Pago: ${est.estado_pago || 'Al día'}</span>
                        </div>
                    </div>
                </div>

                <div class="student-meta">
                    <div class="meta-item"><span>Carrera</span><strong>${est.carrera_codigo}</strong></div>
                    <div class="meta-item"><span>Semestre</span><strong>${est.semestre}º Sem.</strong></div>
                    <div class="meta-item"><span>Promedio</span><strong style="color: ${colorPromedio};">${est.promedio.toFixed(2)} / 5.0</strong></div>
                    <div class="meta-item"><span>Contacto</span><strong style="font-size:0.72rem;" title="${est.email}">${est.email.split('@')[0]}</strong></div>
                </div>

                <div class="student-actions" style="display:flex; gap:0.4rem;">
                    <button class="btn btn-secondary btn-ver-kardex" data-id="${est.id}" style="flex:1;">
                        <i data-lucide="file-text"></i> Kardex
                    </button>
                    <button class="btn btn-secondary btn-pago-notif" data-id="${est.id}" data-nombre="${est.nombre.replace(/"/g, '&quot;')}" data-pago="${est.estado_pago || 'Al día'}" style="flex:1;">
                        <i data-lucide="credit-card"></i> Pago
                    </button>
                </div>
            </article>
        `;
    },

    renderStudentTable(estudiantes) {
        const filas = estudiantes.map(est => {
            const pagoBadgeStyle = est.estado_pago === 'Bloqueado' 
                ? 'background:#fee2e2; color:#991b1b; border:1px solid #fca5a5;'
                : (est.estado_pago === 'Pendiente' ? 'background:#fef3c7; color:#92400e; border:1px solid #fde68a;' : 'background:#dcfce7; color:#166534; border:1px solid #86efac;');

            return `
                <tr>
                    <td>
                        <div style="display:flex; align-items:center; gap:0.6rem;">
                            ${UI.generarAvatarFlatUI(est.nombre, est.id, 30)}
                            <strong>${est.nombre}</strong>
                        </div>
                    </td>
                    <td><code>${est.matricula}</code></td>
                    <td>${est.carrera_nombre} (${est.carrera_codigo})</td>
                    <td>Semestre ${est.semestre}</td>
                    <td>
                        <span class="badge ${est.estado === 'Activo' ? 'badge-activo' : (est.estado === 'En Riesgo' ? 'badge-riesgo' : 'badge-egresado')}">${est.estado}</span>
                        <span class="badge" style="${pagoBadgeStyle}">${est.estado_pago || 'Al día'}</span>
                    </td>
                    <td><strong style="color: ${est.promedio < 3.5 ? '#b91c1c' : '#047857'};">${est.promedio.toFixed(2)}</strong></td>
                    <td>
                        <div style="display:flex; gap:0.3rem;">
                            <button class="btn btn-secondary btn-ver-kardex" data-id="${est.id}" style="padding: 0.25rem 0.55rem; font-size: 0.8rem;">
                                <i data-lucide="file-text"></i> Kardex
                            </button>
                            <button class="btn btn-secondary btn-pago-notif" data-id="${est.id}" data-nombre="${est.nombre.replace(/"/g, '&quot;')}" data-pago="${est.estado_pago || 'Al día'}" style="padding: 0.25rem 0.55rem; font-size: 0.8rem;">
                                <i data-lucide="credit-card"></i> Pago
                            </button>
                        </div>
                    </td>
                </tr>
            `;
        }).join('');

        return `
            <div class="table-container">
                <table class="custom-table">
                    <thead>
                        <tr>
                            <th>Estudiante</th>
                            <th>Matrícula</th>
                            <th>Carrera</th>
                            <th>Semestre</th>
                            <th>Estado</th>
                            <th>Promedio</th>
                            <th>Acciones</th>
                        </tr>
                    </thead>
                    <tbody>${filas}</tbody>
                </table>
            </div>
        `;
    }
};

// =============================================================================
// 4. CONTROLADOR DE LA APLICACIÓN (CONTROLLER)
// =============================================================================
const Controller = {
    async init() {
        console.log("Inicializando Módulo Universitario Institucional.");
        UI.refrescarIconos();

        this.bindEvents();
        await this.cargarDashboard();
        await this.cargarEstudiantes();
        await this.cargarAsignaturas();
        await this.cargarSolicitudesAdmin();
    },

    bindEvents() {
        // Toggle Menú Lateral (Sidebar Collapse)
        const btnToggleSidebar = document.getElementById('btn-toggle-sidebar');
        const sidebar = document.getElementById('sidebar-drawer');

        if (btnToggleSidebar && sidebar) {
            btnToggleSidebar.addEventListener('click', () => {
                sidebar.classList.toggle('collapsed');
            });
        }

        // Navegación Pestañas Sidebar
        document.querySelectorAll('.sidebar-link').forEach(btn => {
            btn.addEventListener('click', () => {
                const target = btn.getAttribute('data-target');
                document.querySelectorAll('.sidebar-link').forEach(b => b.classList.remove('active'));
                document.querySelectorAll('.vista-seccion').forEach(s => s.classList.remove('active'));

                btn.classList.add('active');
                document.getElementById(target).classList.add('active');
                State.vistaActual = target;

                // Actualizar Título en Topbar
                const titleMap = {
                    'vista-dashboard': 'Panel General (Dashboard)',
                    'vista-estudiantes': 'Directorio de Estudiantes (80)',
                    'vista-pensum': 'Catálogo de Pensum y 20 Docentes',
                    'vista-horarios': 'Matriz Semanal de Horarios (7:00 AM - 12:00 PM)',
                    'vista-grupos': 'Gestión de Grupos y Aulas (Máx 15 Alumnos)',
                    'vista-basedatos': 'Visor e Inspector de Base de Datos SQLite',
                    'vista-solicitudes': 'Centro de Solicitudes de Cambio de Horario y Grupo',
                    'vista-usuarios-auth': 'Gestión de Cuentas de Acceso (MB-System)'
                };
                const titleEl = document.getElementById('active-page-title') || document.getElementById('vista-titulo');
                if (titleEl) titleEl.innerText = titleMap[target] || 'Módulo Universitario';

                if (target === 'vista-dashboard') this.cargarDashboard();
                if (target === 'vista-estudiantes') this.cargarEstudiantes();
                if (target === 'vista-pensum') this.cargarAsignaturas();
                if (target === 'vista-horarios') this.cargarHorarios();
                if (target === 'vista-grupos') this.cargarGrupos();
                if (target === 'vista-basedatos') this.cargarBaseDatos();
                if (target === 'vista-solicitudes') this.cargarSolicitudesAdmin();
                if (target === 'vista-usuarios-auth') this.cargarUsuariosAuth();
            });
        });

        // Formulario Crear Cuenta MB-System Admin con Datos Académicos y Generación Automática
        const formCrearAuth = document.getElementById('form-crear-cuenta-admin');
        const selectRoleAuth = document.getElementById('auth-select-role');
        const camposEstudiante = document.getElementById('auth-campos-estudiante');
        const camposProfesor = document.getElementById('auth-campos-profesor');

        const inpPrimerNombre = document.getElementById('auth-inp-primer-nombre');
        const inpSegundoNombre = document.getElementById('auth-inp-segundo-nombre');
        const inpPrimerApellido = document.getElementById('auth-inp-primer-apellido');
        const inpSegundoApellido = document.getElementById('auth-inp-segundo-apellido');
        const previewUser = document.getElementById('preview-username');
        const previewMail = document.getElementById('preview-email');

        const normalizarPreview = (str) => {
            if (!str) return '';
            return str.normalize("NFD").replace(/[\u0300-\u036f]/g, "").replace(/[^a-zA-Z0-9]/g, "").toLowerCase();
        };

        const actualizarPreview = () => {
            const pNom = normalizarPreview(inpPrimerNombre?.value.trim() || '');
            const sNom = normalizarPreview(inpSegundoNombre?.value.trim() || '');
            const pApe = normalizarPreview(inpPrimerApellido?.value.trim() || '');

            if (!pNom || !pApe) {
                if (previewUser) previewUser.innerText = '---';
                if (previewMail) previewMail.innerText = '---@universidad.edu';
                return;
            }

            const baseUser = `${pNom[0]}${sNom ? sNom[0] : ''}${pApe}`;
            if (previewUser) previewUser.innerText = baseUser;
            if (previewMail) previewMail.innerText = `${baseUser}@universidad.edu`;
        };

        [inpPrimerNombre, inpSegundoNombre, inpPrimerApellido].forEach(inp => {
            if (inp) {
                inp.addEventListener('input', actualizarPreview);
            }
        });

        if (selectRoleAuth) {
            selectRoleAuth.addEventListener('change', () => {
                const rol = selectRoleAuth.value;
                if (camposEstudiante) camposEstudiante.style.display = (rol === 'student') ? 'grid' : 'none';
                if (camposProfesor) camposProfesor.style.display = (rol === 'teacher') ? 'grid' : 'none';
                UI.refrescarIconos();
            });
        }

        if (formCrearAuth) {
            formCrearAuth.addEventListener('submit', async (e) => {
                e.preventDefault();
                const alertDiv = document.getElementById('alert-auth-crear');
                if (alertDiv) alertDiv.style.display = 'none';

                const primer_nombre = inpPrimerNombre?.value.trim() || '';
                const segundo_nombre = inpSegundoNombre?.value.trim() || '';
                const primer_apellido = inpPrimerApellido?.value.trim() || '';
                const segundo_apellido = inpSegundoApellido?.value.trim() || '';
                const identificacion = document.getElementById('auth-inp-documento').value.trim();
                const password = document.getElementById('auth-inp-password').value.trim();
                const role = document.getElementById('auth-select-role').value;

                const payload = {
                    primer_nombre,
                    segundo_nombre,
                    primer_apellido,
                    segundo_apellido,
                    identificacion,
                    documento: identificacion,
                    password,
                    role
                };

                if (role === 'student') {
                    payload.carrera_id = document.getElementById('auth-select-carrera')?.value || 'ISW';
                    payload.carrera = payload.carrera_id;
                    payload.semestre = parseInt(document.getElementById('auth-select-semestre')?.value || 1, 10);
                    payload.grupo = document.getElementById('auth-select-grupo')?.value || 'G1';
                } else if (role === 'teacher') {
                    payload.carrera_principal = document.getElementById('auth-select-carrera-prof')?.value || 'ISW';
                    payload.carrera = payload.carrera_principal;
                    payload.departamento = payload.carrera_principal;
                    payload.titulo_academico = document.getElementById('auth-inp-titulo-prof')?.value.trim() || 'Docente Titular';
                }

                try {
                    const res = await API.crearAuthUser(payload);
                    if (alertDiv) {
                        alertDiv.className = 'alert-toast alert-success';
                        alertDiv.innerText = res.mensaje;
                        alertDiv.style.display = 'block';
                        alertDiv.style.background = '#dcfce7';
                        alertDiv.style.color = '#15803d';
                        alertDiv.style.border = '1px solid #86efac';
                    }
                    UI.mostrarToast(res.mensaje, 'success');
                    formCrearAuth.reset();

                    // Restablecer vista previa y visibilidad según rol default
                    if (previewUser) previewUser.innerText = '---';
                    if (previewMail) previewMail.innerText = '---@universidad.edu';

                    if (selectRoleAuth) selectRoleAuth.value = 'student';
                    if (camposEstudiante) camposEstudiante.style.display = 'grid';
                    if (camposProfesor) camposProfesor.style.display = 'none';

                    await this.cargarUsuariosAuth();
                    // Refrescar paneles vinculados
                    if (role === 'student') this.cargarEstudiantes();
                    this.cargarDashboard();
                } catch (err) {
                    if (alertDiv) {
                        alertDiv.className = 'alert-toast alert-error';
                        alertDiv.innerText = err.message || 'Error al crear la cuenta.';
                        alertDiv.style.display = 'block';
                        alertDiv.style.background = '#fee2e2';
                        alertDiv.style.color = '#991b1b';
                        alertDiv.style.border = '1px solid #fca5a5';
                    }
                }
            });
        }

        // Refrescar Solicitudes de Cambio
        document.getElementById('btn-refrescar-solicitudes')?.addEventListener('click', () => {
            this.cargarSolicitudesAdmin();
            UI.mostrarToast("Solicitudes actualizadas", "info");
        });

        // Filtros de Estado en Solicitudes
        document.querySelectorAll('.btn-filtro-solicitud').forEach(btn => {
            btn.addEventListener('click', () => {
                document.querySelectorAll('.btn-filtro-solicitud').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                State.filtroSolicitud = btn.getAttribute('data-filtro');
                this.renderTablaSolicitudes(State.solicitudesCache);
            });
        });


        // Filtros Estudiantes
        document.getElementById('busqueda-input')?.addEventListener('input', this.debounce(() => this.cargarEstudiantes(), 300));
        ['filtro-carrera', 'filtro-semestre', 'filtro-estado', 'filtro-estado-pago'].forEach(id => {
            document.getElementById(id)?.addEventListener('change', () => this.cargarEstudiantes());
        });

        // Filtros Asignaturas (Pensum)
        document.getElementById('busqueda-asg-input')?.addEventListener('input', this.debounce(() => this.cargarAsignaturas(), 300));
        ['filtro-asg-carrera', 'filtro-asg-docente', 'filtro-asg-nivel', 'filtro-asg-tipo'].forEach(id => {
            document.getElementById(id)?.addEventListener('change', () => this.cargarAsignaturas());
        });

        // Filtros Horarios
        ['filtro-horario-carrera', 'filtro-horario-grupo'].forEach(id => {
            document.getElementById(id)?.addEventListener('change', () => this.cargarHorarios());
        });

        // Filtros Grupos
        ['filtro-grupo-carrera', 'filtro-grupo-nivel'].forEach(id => {
            document.getElementById(id)?.addEventListener('change', () => this.cargarGrupos());
        });

        // Alternar vista Grid / Tabla
        document.getElementById('btn-vista-grid')?.addEventListener('click', () => {
            document.getElementById('btn-vista-grid').classList.add('active');
            document.getElementById('btn-vista-tabla').classList.remove('active');
            State.modoVista = 'grid';
            this.cargarEstudiantes();
        });

        document.getElementById('btn-vista-tabla')?.addEventListener('click', () => {
            document.getElementById('btn-vista-tabla').classList.add('active');
            document.getElementById('btn-vista-grid').classList.remove('active');
            State.modoVista = 'tabla';
            this.cargarEstudiantes();
        });

        // Alternar vista Grupos Grid / Tabla
        document.getElementById('btn-grupo-grid')?.addEventListener('click', () => {
            document.getElementById('btn-grupo-grid').classList.add('active');
            document.getElementById('btn-grupo-tabla').classList.remove('active');
            State.modoVistaGrupos = 'grid';
            this.cargarGrupos();
        });

        document.getElementById('btn-grupo-tabla')?.addEventListener('click', () => {
            document.getElementById('btn-grupo-tabla').classList.add('active');
            document.getElementById('btn-grupo-grid').classList.remove('active');
            State.modoVistaGrupos = 'tabla';
            this.cargarGrupos();
        });

        // Restablecer BD
        document.getElementById('btn-reset-db')?.addEventListener('click', async () => {
            if (confirm("¿Restablecer base de datos con los 50 estudiantes originales?")) {
                const res = await API.resetBD();
                UI.mostrarToast(res.mensaje, 'success');
                await this.cargarDashboard();
                await this.cargarEstudiantes();
                await this.cargarAsignaturas();
                if (State.vistaActual === 'vista-basedatos') this.cargarBaseDatos();
            }
        });

        // Modales y Formularios
        document.getElementById('btn-nuevo-estudiante')?.addEventListener('click', () => {
            document.getElementById('form-estudiante').reset();
            document.getElementById('modal-estudiante').classList.add('active');
        });

        document.querySelectorAll('.btn-close-modal').forEach(btn => {
            btn.addEventListener('click', () => {
                document.getElementById('modal-estudiante').classList.remove('active');
                document.getElementById('modal-kardex').classList.remove('active');
                document.getElementById('modal-insertar-db').classList.remove('active');
                document.getElementById('modal-nomina-grupo')?.classList.remove('active');
                document.getElementById('modal-pago-notificacion')?.classList.remove('active');
            });
        });

        document.getElementById('form-estudiante')?.addEventListener('submit', async (e) => {
            e.preventDefault();
            const payload = {
                nombre: document.getElementById('input-nombre').value,
                carrera_id: document.getElementById('input-carrera').value,
                semestre: document.getElementById('input-semestre').value,
                email: document.getElementById('input-email').value,
                telefono: document.getElementById('input-telefono').value,
                estado: document.getElementById('input-estado').value
            };
            try {
                await API.crearEstudiante(payload);
                UI.mostrarToast("Estudiante creado con éxito", "success");
                document.getElementById('modal-estudiante').classList.remove('active');
                this.cargarEstudiantes();
                this.cargarDashboard();
            } catch (err) {
                console.error("Error al registrar estudiante:", err);
            }
        });

        document.getElementById('form-registrar-nota')?.addEventListener('submit', async (e) => {
            e.preventDefault();
            if (!State.estudianteKardexId) return;

            const asgId = document.getElementById('select-materia-nota').value;
            const notaVal = document.getElementById('input-valor-nota').value;

            await API.guardarNota(State.estudianteKardexId, { asignatura_id: asgId, nota: notaVal });
            UI.mostrarToast("Calificación actualizada con éxito", "success");
            this.abrirModalKardex(State.estudianteKardexId);
            this.cargarEstudiantes();
            this.cargarDashboard();
        });

        // Formulario Cambio de Grupo
        document.getElementById('form-cambiar-grupo')?.addEventListener('submit', async (e) => {
            e.preventDefault();
            if (!State.estudianteKardexId) return;

            const asgId = document.getElementById('select-materia-grupo').value;
            const nuevoGrupo = document.getElementById('select-nuevo-grupo').value;

            try {
                const res = await API.cambiarGrupo(State.estudianteKardexId, { asignatura_id: asgId, nuevo_grupo: nuevoGrupo });
                UI.mostrarToast(res.mensaje, 'success');
                this.abrirModalKardex(State.estudianteKardexId);
                this.cargarEstudiantes();
                this.cargarHorarios();
                this.cargarGrupos();
            } catch (err) {
                // El error de validación ya lo muestra UI.mostrarToast
                console.warn("Validación de cambio de grupo rechazada:", err.message);
            }
        });

        // Formulario Gestión de Pago y Notificación
        document.getElementById('form-pago-notificacion')?.addEventListener('submit', async (e) => {
            e.preventDefault();
            const estId = document.getElementById('inp-pago-est-id').value;
            const estado_pago = document.getElementById('select-pago-estado').value;
            const titulo = document.getElementById('inp-pago-titulo-notif').value;
            const mensaje = document.getElementById('inp-pago-mensaje-notif').value;

            try {
                const res = await API.cambiarEstadoPago(estId, { estado_pago, titulo, mensaje });
                UI.mostrarToast(res.mensaje, 'success');
                document.getElementById('modal-pago-notificacion').classList.remove('active');
                await this.cargarEstudiantes();
            } catch (err) {
                console.error("Error al actualizar pago:", err);
            }
        });

        // Submit Formulario Inserción Dinámica a BD
        document.getElementById('form-insertar-db')?.addEventListener('submit', async (e) => {
            e.preventDefault();
            const tabla = document.getElementById('insert-db-tabla-nombre').value;
            const container = document.getElementById('insert-db-fields-container');
            const inputs = container.querySelectorAll('input, select');
            
            const registro = {};
            inputs.forEach(inp => {
                const val = inp.value.trim();
                if (val !== '') {
                    registro[inp.name] = inp.type === 'number' ? parseFloat(val) : val;
                }
            });

            try {
                const res = await API.insertarRegistroBD(tabla, registro);
                UI.mostrarToast(res.mensaje, 'success');
                document.getElementById('modal-insertar-db').classList.remove('active');
                await this.cargarBaseDatos();
                await this.cargarEstudiantes();
                await this.cargarDashboard();
            } catch (err) {
                console.error("Error al insertar registro:", err);
            }
        });
    },

    async cargarDashboard() {
        try {
            const data = await API.getDashboard();
            UI.renderKPICard('kpi-total-estudiantes', data.totalEstudiantes);
            UI.renderKPICard('kpi-promedio-general', data.promedioGeneral.toFixed(2));
            UI.renderKPICard('kpi-estudiantes-riesgo', data.estudiantesRiesgo);
            UI.renderKPICard('kpi-tasa-aprobacion', `${data.tasaAprobacion}%`);
            UI.renderKPICard('kpi-total-docentes', data.totalDocentes);
            UI.renderKPICard('kpi-total-creditos', data.totalCreditos);

            // 1. Renderizar Gráfico SVG Donut de Distribución y Cupos
            this.renderDonutChart(data.distribucionCarreras, data.totalEstudiantes);

            // 2. Barras de distribución por carrera (con límite de 30 cupos)
            const container = document.getElementById('carreras-barras-container');
            if (container && data.distribucionCarreras) {
                container.innerHTML = data.distribucionCarreras.map(item => {
                    const maxCupos = item.cupos_maximos || 30;
                    const ocupados = item.cantidad;
                    const disponibles = maxCupos - ocupados;
                    const pct = (ocupados / maxCupos) * 100;
                    const esLleno = ocupados >= maxCupos;

                    return `
                        <div class="carrera-bar-item">
                            <div class="bar-meta">
                                <strong>${item.nombre} (${item.codigo})</strong>
                                <span>
                                    <span class="badge ${esLleno ? 'badge-riesgo' : 'badge-activo'}">${ocupados} / ${maxCupos} cupos (${pct.toFixed(0)}%)</span>
                                    <small style="margin-left:0.4rem; color:var(--text-light);">${disponibles} libres</small>
                                </span>
                            </div>
                            <div class="bar-bg">
                                <div class="bar-fill" style="width: ${pct}%; background-color: ${item.color};"></div>
                            </div>
                        </div>
                    `;
                }).join('');
            }

            // 3. Barras de promedio comparativo por carrera
            const promContainer = document.getElementById('promedio-carreras-container');
            if (promContainer && data.promedioCarreras) {
                promContainer.innerHTML = data.promedioCarreras.map(item => {
                    const pct = (item.promedio_carrera / 5.0) * 100;
                    return `
                        <div class="carrera-bar-item">
                            <div class="bar-meta">
                                <span>${item.nombre} (${item.codigo})</span>
                                <span style="color:${item.promedio_carrera < 3.5 ? '#b91c1c' : '#047857'}; font-weight:700;">${item.promedio_carrera.toFixed(2)} / 5.0</span>
                            </div>
                            <div class="bar-bg">
                                <div class="bar-fill" style="width: ${pct}%; background-color: ${item.color};"></div>
                            </div>
                        </div>
                    `;
                }).join('');
            }

            // 4. Barras de distribución por semestre
            const semContainer = document.getElementById('semestre-barras-container');
            if (semContainer && data.estudiantesSemestre) {
                semContainer.innerHTML = data.estudiantesSemestre.map(item => {
                    const pct = data.totalEstudiantes > 0 ? (item.cantidad / data.totalEstudiantes) * 100 : 0;
                    return `
                        <div class="carrera-bar-item">
                            <div class="bar-meta">
                                <span>${item.semestre}º Semestre</span>
                                <span>${item.cantidad} alumnos (${pct.toFixed(0)}%)</span>
                            </div>
                            <div class="bar-bg">
                                <div class="bar-fill" style="width: ${pct}%; background-color: #1e3a8a;"></div>
                            </div>
                        </div>
                    `;
                }).join('');
            }

            // 5. Selector de docentes en asignaturas
            const selectDocentes = document.getElementById('filtro-asg-docente');
            if (selectDocentes && data.listaDocentes) {
                selectDocentes.innerHTML = '<option value="">Todos los Docentes (20)</option>' + 
                    data.listaDocentes.map(d => `<option value="${d}">${d}</option>`).join('');
            }

            // 6. Alertas de alumnos en riesgo
            const riesgoContainer = document.getElementById('alertas-riesgo-lista');
            if (riesgoContainer) {
                const enRiesgo = await API.getEstudiantes({ estado: 'En Riesgo' });
                if (enRiesgo.length === 0) {
                    riesgoContainer.innerHTML = '<p class="text-muted" style="font-size:0.85rem;">No hay alumnos en riesgo actualmente.</p>';
                } else {
                    riesgoContainer.innerHTML = enRiesgo.map(est => `
                        <div class="risk-item" onclick="Controller.abrirModalKardex('${est.id}')" title="Ver Kardex del estudiante">
                            <div class="risk-user">
                                ${UI.generarAvatarFlatUI(est.nombre, est.id, 28)}
                                <div>
                                    <div class="risk-name">${est.nombre}</div>
                                    <div class="risk-sub">${est.carrera_codigo} • Semest. ${est.semestre}º</div>
                                </div>
                            </div>
                            <div class="risk-badge">${est.promedio.toFixed(1)}</div>
                        </div>
                    `).join('');
                }
            }
        } catch (err) {
            console.error("Error al cargar dashboard:", err);
        }
    },

    // DIBUJO DINÁMICO DEL GRÁFICO SVG DONUT CON CUPOS POR CARRERA
    renderDonutChart(distribucion, totalEstudiantes) {
        const box = document.getElementById('carreras-donut-svg-box');
        const legend = document.getElementById('carreras-donut-legend');
        if (!box || !legend || !distribucion) return;

        const totalCapacidad = 150; // 5 carreras x 30 cupos
        const radius = 50;
        const circumference = 2 * Math.PI * radius; // ~314.16

        let accumulatedPct = 0;
        const strokeWidth = 24;

        const circlesHTML = distribucion.map(item => {
            const pct = item.cantidad / totalCapacidad;
            const strokeDasharray = `${pct * circumference} ${circumference}`;
            const strokeDashoffset = -accumulatedPct * circumference;
            accumulatedPct += pct;

            return `
                <circle r="${radius}" cx="80" cy="80" fill="transparent"
                        stroke="${item.color}" stroke-width="${strokeWidth}"
                        stroke-dasharray="${strokeDasharray}" stroke-dashoffset="${strokeDashoffset}">
                    <title>${item.nombre}: ${item.cantidad} / ${item.cupos_maximos} cupos</title>
                </circle>
            `;
        }).join('');

        box.innerHTML = `
            <svg width="160" height="160" viewBox="0 0 160 160" style="transform: rotate(-90deg); border-radius:50%;">
                <circle r="${radius}" cx="80" cy="80" fill="transparent" stroke="#e2e8f0" stroke-width="${strokeWidth}"></circle>
                ${circlesHTML}
            </svg>
            <div style="text-align:center; margin-top:-105px; margin-bottom:70px; font-family:var(--font-heading);">
                <strong style="font-size:1.5rem; display:block; color:var(--text-main);">${totalEstudiantes}</strong>
                <span style="font-size:0.7rem; color:var(--text-light); text-transform:uppercase;">/ 150 CUPOS</span>
            </div>
        `;

        legend.innerHTML = distribucion.map(item => `
            <div style="display:flex; align-items:center; gap:0.6rem;">
                <span style="width:12px; height:12px; border-radius:2px; background:${item.color}; flex-shrink:0;"></span>
                <span><strong>${item.codigo}</strong>: ${item.cantidad}/30 cupos ocupados</span>
                <span class="badge badge-activo" style="font-size:0.7rem;">${30 - item.cantidad} libres</span>
            </div>
        `).join('');
    },

    async cargarEstudiantes() {
        const params = {
            q: document.getElementById('busqueda-input')?.value || '',
            carrera_id: document.getElementById('filtro-carrera')?.value || '',
            semestre: document.getElementById('filtro-semestre')?.value || '',
            estado: document.getElementById('filtro-estado')?.value || '',
            estado_pago: document.getElementById('filtro-estado-pago')?.value || ''
        };

        const estudiantes = await API.getEstudiantes(params);
        const contenedor = document.getElementById('estudiantes-contenedor');
        if (!contenedor) return;

        if (estudiantes.length === 0) {
            contenedor.innerHTML = '<div style="grid-column: 1/-1; text-align: center; padding: 2rem; color: #64748b;">No se encontraron estudiantes con los criterios especificados.</div>';
            return;
        }

        if (State.modoVista === 'grid') {
            contenedor.className = 'estudiantes-grid';
            contenedor.innerHTML = estudiantes.map(UI.renderStudentCard).join('');
        } else {
            contenedor.className = 'table-container';
            contenedor.innerHTML = UI.renderStudentTable(estudiantes);
        }

        UI.refrescarIconos();
        contenedor.querySelectorAll('.btn-ver-kardex').forEach(btn => {
            btn.addEventListener('click', () => this.abrirModalKardex(btn.getAttribute('data-id')));
        });
        contenedor.querySelectorAll('.btn-pago-notif').forEach(btn => {
            btn.addEventListener('click', () => this.abrirModalPagoNotificacion(
                btn.getAttribute('data-id'),
                btn.getAttribute('data-nombre'),
                btn.getAttribute('data-pago')
            ));
        });
    },

    async cargarAsignaturas() {
        const params = {
            q: document.getElementById('busqueda-asg-input')?.value || '',
            carrera_id: document.getElementById('filtro-asg-carrera')?.value || '',
            docente: document.getElementById('filtro-asg-docente')?.value || '',
            nivel: document.getElementById('filtro-asg-nivel')?.value || '',
            tipo: document.getElementById('filtro-asg-tipo')?.value || ''
        };

        const asignaturas = await API.getAsignaturas(params);
        const contenedor = document.getElementById('asignaturas-contenedor');
        if (!contenedor) return;

        if (asignaturas.length === 0) {
            contenedor.innerHTML = '<div style="grid-column: 1/-1; text-align: center; padding: 2rem; color: #64748b;">No se encontraron asignaturas con los criterios de filtro seleccionados.</div>';
            return;
        }

        contenedor.innerHTML = asignaturas.map(asg => `
            <div class="asignatura-card">
                <div class="asg-header">
                    <span class="asg-code">${asg.codigo}</span>
                    <span class="asg-level-badge level-${asg.nivel}">Nivel ${asg.nivel}</span>
                </div>
                <h4 class="asg-title">${asg.nombre}</h4>
                <div style="margin:0.2rem 0;">
                    <span class="badge ${asg.tipo === 'exclusiva' ? 'badge-activo' : 'badge-egresado'}">
                        ${asg.tipo === 'exclusiva' ? `Exclusiva (${asg.carrera_id})` : 'Compartida / General'}
                    </span>
                    <span class="badge badge-activo" style="margin-left:0.3rem;">${asg.grupo} • ${asg.aula}</span>
                </div>
                <div style="font-size:0.8rem; color:var(--primary); font-weight:600; margin-top:0.25rem;">
                    <i data-lucide="clock" style="width:14px; height:14px; vertical-align:middle;"></i> ${asg.horario}
                </div>
                <div class="asg-footer" style="margin-top:0.5rem; border-top:1px solid #f1f5f9; padding-top:0.5rem;">
                    <span><i data-lucide="user"></i> <strong>${asg.docente}</strong></span>
                    <span><strong>${asg.creditos} Créditos</strong></span>
                </div>
            </div>
        `).join('');

        UI.refrescarIconos();
    },

    // MATRIZ SEMANAL DE HORARIOS (7:00 AM - 12:00 PM) EN BLOQUES DE 2 HORAS
    async cargarHorarios() {
        const carreraId = document.getElementById('filtro-horario-carrera')?.value || '';
        const grupo = document.getElementById('filtro-horario-grupo')?.value || '';

        const params = {};
        if (carreraId) params.carrera_id = carreraId;

        const asignaturas = await API.getAsignaturas(params);
        const tbody = document.getElementById('tbody-matriz-horarios');
        if (!tbody) return;

        // Filtrar por grupo si fue seleccionado
        const filtradas = grupo ? asignaturas.filter(a => a.grupo === grupo) : asignaturas;

        const bloques = [
            { id: "07:00-09:00", label: "07:00 - 09:00", sub: "Bloque 1" },
            { id: "09:00-11:00", label: "09:00 - 11:00", sub: "Bloque 2" },
            { id: "10:00-12:00", label: "10:00 - 12:00", sub: "Bloque 3 / Prácticas" }
        ];

        const diasSemana = ["Lun", "Mar", "Mié", "Jue", "Vie"];

        tbody.innerHTML = bloques.map(b => {
            const celdasDias = diasSemana.map(dia => {
                const asgsEnBloque = filtradas.filter(a => {
                    return a.horario.includes(dia) && a.horario.includes(b.id);
                });

                if (asgsEnBloque.length === 0) {
                    return `<td style="color:#94a3b8; font-size:0.78rem; text-align:center; vertical-align:middle; background:#fafafa;">Libre</td>`;
                }

                const cardsHTML = asgsEnBloque.map(a => `
                    <div style="background:#f0f9ff; border:1px solid #bae6fd; border-radius:4px; padding:0.5rem; margin-bottom:0.4rem; font-size:0.78rem;">
                        <div style="font-weight:700; color:#0369a1;"><code>${a.codigo}</code> ${a.nombre}</div>
                        <div style="color:#0f172a; margin:0.15rem 0; display:inline-flex; align-items:center; gap:3px;">
                            <i data-lucide="user-check" style="width:12px; height:12px;"></i> <span>${a.docente}</span>
                        </div>
                        <div style="display:flex; justify-content:space-between; font-size:0.72rem; color:#475569;">
                            <span>${a.grupo} • ${a.aula}</span>
                            <strong>Nivel ${a.nivel}</strong>
                        </div>
                    </div>
                `).join('');

                return `<td>${cardsHTML}</td>`;
            }).join('');

            return `
                <tr>
                    <td style="text-align:center; font-weight:700; background:#f8fafc;">
                        <div>${b.label}</div>
                        <small style="color:var(--text-light); font-weight:normal;">${b.sub}</small>
                    </td>
                    ${celdasDias}
                </tr>
            `;
        }).join('');

        UI.refrescarIconos();
    },

    // GESTIÓN DE GRUPOS DE ESTUDIO Y AULAS (MÁX 10 EXCLUSIVA | 15 COMPARTIDA)
    async cargarGrupos() {
        const params = {
            carrera_id: document.getElementById('filtro-grupo-carrera')?.value || ''
        };

        const nivelFiltro = document.getElementById('filtro-grupo-nivel')?.value || '';
        const grupos = await API.getGrupos(params);
        const contenedor = document.getElementById('grupos-contenedor');
        if (!contenedor) return;

        let filtrados = grupos;
        if (nivelFiltro) {
            filtrados = grupos.filter(g => String(g.nivel) === nivelFiltro);
        }

        if (filtrados.length === 0) {
            contenedor.innerHTML = '<div style="grid-column: 1/-1; text-align: center; padding: 2rem; color: #64748b;">No se encontraron grupos de estudio con los criterios seleccionados.</div>';
            return;
        }

        if (State.modoVistaGrupos === 'tabla') {
            contenedor.className = 'table-container';
            contenedor.innerHTML = `
                <table class="custom-table">
                    <thead>
                        <tr>
                            <th>Sección</th>
                            <th>Asignatura</th>
                            <th>Tipo</th>
                            <th>Nivel</th>
                            <th>Docente</th>
                            <th>Horario</th>
                            <th>Aula</th>
                            <th>Aforo Ocupado</th>
                            <th>Acciones</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${filtrados.map(g => {
                            const maxCupos = g.tipo === 'exclusiva' ? 10 : 15;
                            const pct = Math.min(100, Math.round((g.inscritos / maxCupos) * 100));
                            const badgeClass = g.inscritos >= maxCupos ? 'badge-riesgo' : 'badge-activo';

                            return `
                                <tr>
                                    <td><code>${g.codigo_seccion}</code></td>
                                    <td><strong>${g.nombre}</strong></td>
                                    <td><span class="badge ${g.tipo === 'exclusiva' ? 'badge-activo' : 'badge-egresado'}">${g.tipo}</span></td>
                                    <td><span class="asg-level-badge level-${g.nivel}">Nivel ${g.nivel}</span></td>
                                    <td>${g.docente}</td>
                                    <td><i data-lucide="clock" style="width:13px; height:13px; vertical-align:middle;"></i> ${g.horario}</td>
                                    <td><strong>${g.aula}</strong></td>
                                    <td>
                                        <div style="font-size:0.8rem; font-weight:700;">${g.inscritos} / ${maxCupos} (${g.cupos_libres} libres)</div>
                                        <div style="height:5px; background:#e2e8f0; border-radius:3px; overflow:hidden; margin-top:2px;">
                                            <div style="width:${pct}%; height:100%; background:${g.inscritos >= maxCupos ? '#b91c1c' : '#1e3a8a'};"></div>
                                        </div>
                                    </td>
                                    <td>
                                        <button class="btn btn-secondary" style="padding:0.25rem 0.55rem; font-size:0.78rem;" onclick="Controller.verAlumnosGrupo('${g.asignatura_id}', '${g.grupo}', '${g.nombre.replace(/'/g, "\\'")}')">
                                            <i data-lucide="users" style="width:13px; height:13px;"></i> Alumnos (${g.inscritos})
                                        </button>
                                    </td>
                                </tr>
                            `;
                        }).join('')}
                    </tbody>
                </table>
            `;
        } else {
            contenedor.className = 'asignaturas-grid';
            contenedor.innerHTML = filtrados.map(g => {
                const maxCupos = g.tipo === 'exclusiva' ? 10 : 15;
                const pct = Math.min(100, Math.round((g.inscritos / maxCupos) * 100));
                const badgeClass = g.inscritos >= maxCupos ? 'badge-riesgo' : 'badge-activo';

                return `
                    <div class="grupo-card-compact" style="border-left: 4px solid var(--primary);">
                        <div class="grupo-header-compact">
                            <span class="asg-code"><code>${g.codigo_seccion}</code></span>
                            <span class="badge ${badgeClass}">${g.estado_aula}</span>
                        </div>
                        <h4 style="font-family:var(--font-heading); font-size:0.95rem; font-weight:700;">${g.nombre}</h4>
                        <div style="font-size:0.78rem; color:var(--text-muted); display:flex; justify-content:space-between;">
                            <span>Nivel ${g.nivel} (${g.tipo})</span>
                            <span>${g.aula}</span>
                        </div>

                        <div style="margin: 0.2rem 0;">
                            <div class="grupo-meta-compact">
                                <span>Aforo máx: ${maxCupos}</span>
                                <span><strong>${g.inscritos}/${maxCupos}</strong> (${g.cupos_libres} libres)</span>
                            </div>
                            <div class="grupo-progress-compact">
                                <div class="grupo-progress-fill" style="width:${pct}%; background:${g.inscritos >= maxCupos ? '#b91c1c' : '#1e3a8a'};"></div>
                            </div>
                        </div>

                        <div style="font-size:0.78rem; color:var(--text-muted); display:flex; justify-content:space-between; align-items:center; border-top:1px solid #f1f5f9; padding-top:0.4rem;">
                            <span>Docente: <strong>${g.docente}</strong></span>
                            <button class="btn btn-secondary" style="padding:0.25rem 0.5rem; font-size:0.75rem;" onclick="Controller.verAlumnosGrupo('${g.asignatura_id}', '${g.grupo}', '${g.nombre.replace(/'/g, "\\'")}')">
                                <i data-lucide="users" style="width:12px; height:12px;"></i> Nómina (${g.inscritos})
                            </button>
                        </div>
                    </div>
                `;
            }).join('');
        }

        UI.refrescarIconos();
    },

    // VISOR ACORDEÓN BASE DE DATOS
    async cargarBaseDatos() {
        try {
            const data = await API.getDatabaseInfo();
            State.dbCache = data;
            const container = document.getElementById('db-accordion-container');
            if (!container) return;

            container.innerHTML = Object.entries(data).map(([tabla, info]) => {
                const isOpen = State.tablasAbiertas.has(tabla);
                const cols = info.columnas;
                const rows = info.muestra;

                return `
                    <div class="db-table-item" id="db-item-${tabla}">
                        <div class="db-table-header ${isOpen ? 'open' : ''}" onclick="Controller.toggleTablaAcordeon('${tabla}')">
                            <div class="db-table-title">
                                <i data-lucide="${isOpen ? 'folder-open' : 'folder'}"></i>
                                <span>Tabla <code>${tabla}</code></span>
                                <span class="badge badge-activo">${info.totalRegistros} registros</span>
                            </div>
                            <div class="db-table-actions">
                                <i data-lucide="${isOpen ? 'chevron-up' : 'chevron-down'}"></i>
                            </div>
                        </div>

                        <div class="db-table-content ${isOpen ? 'open' : ''}">
                            <div class="db-table-toolbar">
                                <div class="search-group" style="max-width:320px;">
                                    <i data-lucide="search" class="search-icon"></i>
                                    <input type="text" id="filter-db-${tabla}" placeholder="Filtrar en ${tabla}..." oninput="Controller.filtrarTablaBD('${tabla}')">
                                </div>
                                <button class="btn btn-success" onclick="Controller.abrirModalInsertarBD('${tabla}')">
                                    <i data-lucide="plus"></i> Añadir Registro a ${tabla}
                                </button>
                            </div>

                            <div class="table-container">
                                <table class="custom-table" id="table-db-${tabla}" style="font-size:0.82rem;">
                                    <thead>
                                        <tr>${cols.map(c => `<th>${c}</th>`).join('')}</tr>
                                    </thead>
                                    <tbody id="tbody-db-${tabla}">
                                        ${this.renderFilasTablaBD(cols, rows)}
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    </div>
                `;
            }).join('');

            UI.refrescarIconos();
        } catch (err) {
            console.error("Error al cargar visor de base de datos:", err);
        }
    },

    renderFilasTablaBD(cols, rows) {
        if (!rows || rows.length === 0) {
            return `<tr><td colspan="${cols.length}" style="text-align:center; padding:1rem; color:#64748b;">No hay registros en esta tabla.</td></tr>`;
        }
        return rows.map(r => `
            <tr>
                ${cols.map(c => `<td><code>${r[c] !== null ? r[c] : '<em style="color:#94a3b8;">NULL</em>'}</code></td>`).join('')}
            </tr>
        `).join('');
    },

    toggleTablaAcordeon(tabla) {
        if (State.tablasAbiertas.has(tabla)) {
            State.tablasAbiertas.delete(tabla);
        } else {
            State.tablasAbiertas.add(tabla);
        }
        this.cargarBaseDatos();
    },

    filtrarTablaBD(tabla) {
        const query = document.getElementById(`filter-db-${tabla}`)?.value.toLowerCase() || '';
        const info = State.dbCache ? State.dbCache[tabla] : null;
        if (!info) return;

        const cols = info.columnas;
        const filtradas = info.muestra.filter(row => {
            return cols.some(c => String(row[c] || '').toLowerCase().includes(query));
        });

        const tbody = document.getElementById(`tbody-db-${tabla}`);
        if (tbody) {
            tbody.innerHTML = this.renderFilasTablaBD(cols, filtradas);
        }
    },

    abrirModalInsertarBD(tabla) {
        const info = State.dbCache ? State.dbCache[tabla] : null;
        if (!info) return;

        document.getElementById('insert-db-tabla-nombre').value = tabla;
        document.getElementById('modal-insertar-titulo').innerHTML = `<i data-lucide="shield-check"></i> Registrar en Tabla: <code>${tabla}</code>`;

        const container = document.getElementById('insert-db-fields-container');

        const opcionesCarreras = [
            { id: 'ISW', nombre: 'Ingeniería de Software (ISW)' },
            { id: 'MED', nombre: 'Medicina Humana (MED)' },
            { id: 'ADM', nombre: 'Administración de Empresas (ADM)' },
            { id: 'DER', nombre: 'Derecho y C. Políticas (DER)' },
            { id: 'ARQ', nombre: 'Arquitectura y Urbanismo (ARQ)' }
        ];

        container.innerHTML = info.columnasDetalle.map(col => {
            const nom = col.nombre;
            const label = col.etiqueta || nom;
            const isPK = col.pk === 1;

            if (nom === 'carrera_id' || nom === 'carrera_principal') {
                return `
                    <div class="form-group">
                        <label for="inp-db-${nom}"><strong>${label}</strong> *</label>
                        <select id="inp-db-${nom}" name="${nom}" required style="padding:0.55rem; border:1px solid var(--border-color); border-radius:4px; font-size:0.85rem; background:#fff;">
                            ${opcionesCarreras.map(c => `<option value="${c.id}">${c.nombre}</option>`).join('')}
                        </select>
                    </div>
                `;
            }

            if (nom === 'estado') {
                return `
                    <div class="form-group">
                        <label for="inp-db-${nom}"><strong>${label}</strong></label>
                        <select id="inp-db-${nom}" name="${nom}" style="padding:0.55rem; border:1px solid var(--border-color); border-radius:4px; font-size:0.85rem; background:#fff;">
                            <option value="Activo">Activo</option>
                            <option value="En Riesgo">En Riesgo (&lt; 3.5)</option>
                            <option value="Egresado">Egresado</option>
                            <option value="Licencia">Licencia</option>
                        </select>
                    </div>
                `;
            }

            if (nom === 'tipo') {
                return `
                    <div class="form-group">
                        <label for="inp-db-${nom}"><strong>${label}</strong></label>
                        <select id="inp-db-${nom}" name="${nom}" style="padding:0.55rem; border:1px solid var(--border-color); border-radius:4px; font-size:0.85rem; background:#fff;">
                            <option value="exclusiva">Exclusiva de Carrera</option>
                            <option value="compartida">Compartida / General</option>
                        </select>
                    </div>
                `;
            }

            if (nom === 'nivel') {
                return `
                    <div class="form-group">
                        <label for="inp-db-${nom}"><strong>${label}</strong></label>
                        <select id="inp-db-${nom}" name="${nom}" style="padding:0.55rem; border:1px solid var(--border-color); border-radius:4px; font-size:0.85rem; background:#fff;">
                            <option value="1">Nivel 1 (Fundamentos)</option>
                            <option value="2">Nivel 2 (Intermedio)</option>
                            <option value="3">Nivel 3 (Avanzado)</option>
                        </select>
                    </div>
                `;
            }

            if (nom === 'semestre') {
                return `
                    <div class="form-group">
                        <label for="inp-db-${nom}"><strong>${label}</strong></label>
                        <select id="inp-db-${nom}" name="${nom}" style="padding:0.55rem; border:1px solid var(--border-color); border-radius:4px; font-size:0.85rem; background:#fff;">
                            ${[1,2,3,4,5,6,7,8].map(s => `<option value="${s}">${s}º Semestre</option>`).join('')}
                        </select>
                    </div>
                `;
            }

            if (nom === 'horario') {
                return `
                    <div class="form-group">
                        <label for="inp-db-${nom}"><strong>${label}</strong></label>
                        <select id="inp-db-${nom}" name="${nom}" style="padding:0.55rem; border:1px solid var(--border-color); border-radius:4px; font-size:0.85rem; background:#fff;">
                            <option value="Lun-Mié 07:00-09:00">Lun-Mié 07:00 - 09:00 (Bloque 1)</option>
                            <option value="Lun-Mié 09:00-11:00">Lun-Mié 09:00 - 11:00 (Bloque 2)</option>
                            <option value="Lun-Mié 10:00-12:00">Lun-Mié 10:00 - 12:00 (Bloque 3)</option>
                            <option value="Mar-Jue 07:00-09:00">Mar-Jue 07:00 - 09:00 (Bloque 1)</option>
                            <option value="Mar-Jue 09:00-11:00">Mar-Jue 09:00 - 11:00 (Bloque 2)</option>
                            <option value="Mar-Jue 10:00-12:00">Mar-Jue 10:00 - 12:00 (Bloque 3)</option>
                            <option value="Viernes 07:00-09:00">Viernes 07:00 - 09:00</option>
                            <option value="Viernes 09:00-11:00">Viernes 09:00 - 11:00</option>
                            <option value="Viernes 10:00-12:00">Viernes 10:00 - 12:00</option>
                        </select>
                    </div>
                `;
            }

            const isNum = col.tipo.includes('INT') || col.tipo.includes('REAL');
            return `
                <div class="form-group">
                    <label for="inp-db-${nom}">
                        <strong>${label}</strong> ${col.notnull ? '*' : ''}
                        ${isPK ? '<small style="color:var(--primary);">(Clave Única)</small>' : ''}
                    </label>
                    <input type="${isNum ? 'number' : 'text'}" 
                           step="${col.tipo.includes('REAL') ? '0.1' : '1'}"
                           id="inp-db-${nom}" 
                           name="${nom}" 
                           placeholder="Ingresar ${label.toLowerCase()}..." 
                           ${col.notnull && !isPK ? 'required' : ''}
                           style="padding:0.55rem; border:1px solid var(--border-color); border-radius:4px; font-size:0.85rem;">
                </div>
            `;
        }).join('');

        document.getElementById('modal-insertar-db').classList.add('active');
        UI.refrescarIconos();
    },

    async abrirModalKardex(estudianteId) {
        State.estudianteKardexId = estudianteId;
        const est = await API.getDetalleEstudiante(estudianteId);
        const modal = document.getElementById('modal-kardex');

        document.getElementById('kardex-perfil-header').innerHTML = `
            <img src="${est.foto_avatar}" width="54" height="54" style="border-radius:50%;">
            <div>
                <h3 style="font-family:var(--font-heading);">${est.nombre}</h3>
                <p style="font-size:0.85rem; color:var(--text-muted);">
                    Matrícula: <code>${est.matricula}</code> • ${est.carrera_nombre} • Semestre ${est.semestre}º
                </p>
                <div style="margin-top:0.3rem;">
                    <span class="badge ${est.estado === 'Activo' ? 'badge-activo' : (est.estado === 'En Riesgo' ? 'badge-riesgo' : 'badge-egresado')}">${est.estado}</span>
                    <span style="margin-left:0.75rem; font-weight:700;">
                        Promedio: <span style="color: ${est.promedio < 3.5 ? '#b91c1c' : '#047857'}; font-size:1.1rem;">${est.promedio.toFixed(2)}</span> / 5.0
                    </span>
                </div>
            </div>
        `;

        const materias = await API.getAsignaturas({ carrera_id: est.carrera_id });
        const selectNota = document.getElementById('select-materia-nota');
        selectNota.innerHTML = '<option value="">Seleccionar Asignatura para Calificar...</option>';
        materias.forEach(a => {
            selectNota.innerHTML += `<option value="${a.id}">[Nivel ${a.nivel}] ${a.codigo} - ${a.nombre} (${a.creditos} crd)</option>`;
        });

        const selectGrupo = document.getElementById('select-materia-grupo');
        if (selectGrupo) {
            selectGrupo.innerHTML = '<option value="">Seleccionar Asignatura Inscrita...</option>';
            if (est.inscripciones) {
                est.inscripciones.forEach(i => {
                    selectGrupo.innerHTML += `<option value="${i.asignatura_id}">[Nivel ${i.nivel}] ${i.codigo} - ${i.nombre}</option>`;
                });
            }
        }

        const tbody = document.getElementById('kardex-tabla-body');
        if (!est.inscripciones || est.inscripciones.length === 0) {
            tbody.innerHTML = '<tr><td colspan="7" style="text-align:center; padding:1.5rem; color:#64748b;">Sin calificaciones. Registra notas arriba.</td></tr>';
        } else {
            tbody.innerHTML = est.inscripciones.map(i => `
                <tr>
                    <td><code>${i.codigo}</code></td>
                    <td><strong>${i.nombre}</strong></td>
                    <td><span class="asg-level-badge level-${i.nivel}">Nivel ${i.nivel}</span></td>
                    <td>${i.creditos} crd</td>
                    <td>${i.docente}</td>
                    <td><strong style="font-size:1rem; color:${i.nota < 3.5 ? '#b91c1c' : '#047857'};">${i.nota.toFixed(1)}</strong></td>
                    <td><span class="badge ${i.nota >= 3.5 ? 'badge-activo' : 'badge-riesgo'}">${i.nota >= 3.5 ? 'Aprobado' : 'Desaprobado'}</span></td>
                </tr>
            `).join('');
        }

        this.switchSubtabKardex('kardex');
        await this.cargarHorarioEstudiante(estudianteId);
        modal.classList.add('active');
    },

    switchSubtabKardex(tab) {
        const btnKardex = document.getElementById('btn-tab-kardex');
        const btnHorario = document.getElementById('btn-tab-horario');
        const subKardex = document.getElementById('subseccion-kardex');
        const subHorario = document.getElementById('subseccion-horario');

        if (tab === 'horario') {
            btnKardex.className = 'btn btn-secondary';
            btnHorario.className = 'btn btn-primary';
            subKardex.style.display = 'none';
            subHorario.style.display = 'block';
        } else {
            btnKardex.className = 'btn btn-primary';
            btnHorario.className = 'btn btn-secondary';
            subKardex.style.display = 'block';
            subHorario.style.display = 'none';
        }
    },

    async cargarHorarioEstudiante(estudianteId) {
        try {
            const res = await API.getHorarioEstudiante(estudianteId);
            const tbody = document.getElementById('tbody-horario-individual');
            if (!tbody) return;

            const bloques = [
                { hora: "07:00-09:00", label: "07:00 AM - 09:00 AM" },
                { hora: "09:00-11:00", label: "09:00 AM - 11:00 AM" },
                { hora: "10:00-12:00", label: "10:00 AM - 12:00 PM" }
            ];
            const dias = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes"];

            tbody.innerHTML = bloques.map(b => {
                const celdas = dias.map(d => {
                    const materias = res.matriz_horario[b.hora][d] || [];
                    if (materias.length === 0) {
                        return '<td style="background:#fafafa; color:#cbd5e1; text-align:center; font-size:0.75rem;">— Libre —</td>';
                    }
                    const cards = materias.map(m => `
                        <div style="background:#eff6ff; border:1px solid #bfdbfe; border-left:3px solid var(--primary); padding:0.4rem; border-radius:4px; font-size:0.75rem; margin-bottom:0.25rem;">
                            <div style="font-weight:700; color:var(--primary);"><code>${m.codigo}</code> • ${m.nombre}</div>
                            <div style="color:var(--text-muted); font-size:0.7rem; margin-top:2px;">
                                <span style="display:inline-flex; align-items:center; gap:3px;"><i data-lucide="user-check" style="width:12px; height:12px;"></i> ${m.docente}</span><br>
                                <span style="display:inline-flex; align-items:center; gap:3px;"><i data-lucide="map-pin" style="width:12px; height:12px;"></i> ${m.grupo} • ${m.aula}</span>
                            </div>
                        </div>
                    `).join('');
                    return `<td>${cards}</td>`;
                }).join('');

                return `
                    <tr>
                        <td style="text-align:center; font-weight:700; background:#f8fafc; font-size:0.8rem;">${b.label}</td>
                        ${celdas}
                    </tr>
                `;
            }).join('');

            UI.refrescarIconos();
        } catch (err) {
            console.error("Error al cargar horario del estudiante:", err);
        }
    },

    async verAlumnosGrupo(asignaturaId, grupo, asignaturaNombre) {
        try {
            const res = await API.getEstudiantesGrupo(asignaturaId, grupo);
            const title = document.getElementById('modal-nomina-titulo');
            const sub = document.getElementById('modal-nomina-sub');
            const tbody = document.getElementById('tbody-nomina-estudiantes');
            const modal = document.getElementById('modal-nomina-grupo');

            if (title) title.innerHTML = `<i data-lucide="users"></i> Nómina de Alumnos: ${asignaturaNombre} (${grupo})`;
            if (sub) sub.innerHTML = `Total de estudiantes matriculados: <strong>${res.total_inscritos} alumnos</strong> en la sección ${grupo}`;

            if (tbody) {
                if (res.estudiantes.length === 0) {
                    tbody.innerHTML = '<tr><td colspan="8" style="text-align:center; padding:1.5rem; color:#64748b;">No hay estudiantes inscritos en esta sección.</td></tr>';
                } else {
                    tbody.innerHTML = res.estudiantes.map(e => `
                        <tr>
                            <td><img src="${e.foto_avatar}" width="32" height="32" style="border-radius:50%;"></td>
                            <td><code>${e.matricula}</code></td>
                            <td><strong>${e.nombre}</strong></td>
                            <td>${e.carrera_nombre}</td>
                            <td>${e.semestre}º Semestre</td>
                            <td><strong style="color:${e.promedio < 3.5 ? '#b91c1c' : '#047857'};">${e.promedio.toFixed(2)}</strong></td>
                            <td><strong style="color:${e.nota < 3.5 ? '#b91c1c' : '#047857'};">${e.nota.toFixed(1)}</strong></td>
                            <td><span class="badge ${e.estado === 'Activo' ? 'badge-activo' : (e.estado === 'En Riesgo' ? 'badge-riesgo' : 'badge-egresado')}">${e.estado}</span></td>
                        </tr>
                    `).join('');
                }
            }

            if (modal) modal.classList.add('active');
            UI.refrescarIconos();
        } catch (err) {
            console.error("Error al obtener nómina de alumnos:", err);
        }
    },

    abrirModalPagoNotificacion(estId, nombre, estadoPago) {
        document.getElementById('inp-pago-est-id').value = estId;
        document.getElementById('modal-pago-titulo').innerHTML = `<i data-lucide="credit-card"></i> Gestión Financiera: ${nombre}`;
        document.getElementById('modal-pago-sub').innerText = `Estudiante ID: ${estId} • Tesorería Universitaria`;
        document.getElementById('select-pago-estado').value = estadoPago || 'Al día';
        document.getElementById('inp-pago-titulo-notif').value = '';
        document.getElementById('inp-pago-mensaje-notif').value = '';
        
        document.getElementById('modal-pago-notificacion').classList.add('active');
        UI.refrescarIconos();
    },

    async cargarSolicitudesAdmin() {
        try {
            const data = await API.getSolicitudesAdmin();
            State.solicitudesCache = data.solicitudes || [];

            // Actualizar KPIs de Solicitudes
            const totalEl = document.getElementById('kpi-solicitudes-total');
            const pendEl = document.getElementById('kpi-solicitudes-pendientes');
            const aprobEl = document.getElementById('kpi-solicitudes-aprobadas');
            const rechEl = document.getElementById('kpi-solicitudes-rechazadas');
            const navBadge = document.getElementById('badge-nav-solicitudes-pendientes');

            if (totalEl) totalEl.innerText = data.total || 0;
            if (pendEl) pendEl.innerText = data.pendientes || 0;
            if (aprobEl) aprobEl.innerText = data.aprobadas || 0;
            if (rechEl) rechEl.innerText = data.rechazadas || 0;

            if (navBadge) {
                if (data.pendientes > 0) {
                    navBadge.style.display = 'inline-block';
                    navBadge.innerText = data.pendientes;
                } else {
                    navBadge.style.display = 'none';
                }
            }

            this.renderTablaSolicitudes(State.solicitudesCache);
        } catch (err) {
            console.error("Error al cargar solicitudes de administración:", err);
        }
    },

    renderTablaSolicitudes(solicitudes) {
        const tbody = document.getElementById('tbody-admin-solicitudes');
        if (!tbody) return;

        let filtradas = solicitudes;
        if (State.filtroSolicitud && State.filtroSolicitud !== 'TODAS') {
            filtradas = solicitudes.filter(s => s.estado === State.filtroSolicitud);
        }

        if (filtradas.length === 0) {
            tbody.innerHTML = '<tr><td colspan="9" style="text-align:center; padding:2rem; color:#64748b;">No hay solicitudes registradas con el filtro seleccionado.</td></tr>';
            return;
        }

        tbody.innerHTML = filtradas.map(s => {
            let badgeHtml = '';
            if (s.estado === 'PENDIENTE') {
                badgeHtml = '<span class="badge" style="background:#fef3c7; color:#92400e; border:1px solid #fde68a; display:inline-flex; align-items:center; gap:4px;"><i data-lucide="clock" style="width:12px; height:12px;"></i> PENDIENTE</span>';
            } else if (s.estado === 'APROBADO') {
                badgeHtml = '<span class="badge badge-activo" style="display:inline-flex; align-items:center; gap:4px;"><i data-lucide="check-circle-2" style="width:12px; height:12px;"></i> APROBADO</span>';
            } else {
                badgeHtml = '<span class="badge badge-riesgo" style="display:inline-flex; align-items:center; gap:4px;"><i data-lucide="x-circle" style="width:12px; height:12px;"></i> RECHAZADO</span>';
            }

            let accionesHtml = '';
            if (s.estado === 'PENDIENTE') {
                accionesHtml = `
                    <div style="display:flex; gap:0.4rem; justify-content:center;">
                        <button class="btn btn-sm btn-primary" onclick="Controller.dictaminarSolicitud(${s.id}, 'aprobar')" style="background:#16a34a; border-color:#15803d; padding:0.35rem 0.65rem; font-size:0.75rem; display:inline-flex; align-items:center; gap:4px;" title="Aprobar cambio y reasignar grupo">
                            <i data-lucide="check-circle-2" style="width:13px; height:13px;"></i> Aprobar
                        </button>
                        <button class="btn btn-sm btn-outline-danger" onclick="Controller.dictaminarSolicitud(${s.id}, 'rechazar')" style="padding:0.35rem 0.65rem; font-size:0.75rem; display:inline-flex; align-items:center; gap:4px;" title="Rechazar solicitud">
                            <i data-lucide="x-circle" style="width:13px; height:13px;"></i> Rechazar
                        </button>
                    </div>
                `;
            } else {
                accionesHtml = `
                    <div style="font-size:0.75rem; color:#64748b; text-align:center;">
                        <span>Resuelto el ${s.fecha_resolucion || s.fecha}</span>
                    </div>
                `;
            }

            return `
                <tr>
                    <td><strong>#${s.id}</strong></td>
                    <td style="font-size:0.78rem; color:#64748b;">${s.fecha}</td>
                    <td>
                        <div style="display:flex; align-items:center; gap:0.5rem;">
                            ${UI.generarAvatarFlatUI(s.estudiante_nombre, s.estudiante_id, 32)}
                            <div>
                                <strong style="color:var(--text-main);">${s.estudiante_nombre}</strong><br>
                                <code style="font-size:0.72rem;">${s.estudiante_id}</code>
                            </div>
                        </div>
                    </td>
                    <td><span class="badge badge-carrera">${s.carrera_id}</span></td>
                    <td>
                        <strong style="color:var(--primary);">${s.asignatura_nombre}</strong><br>
                        <code style="font-size:0.72rem;">${s.asignatura_codigo}</code>
                    </td>
                    <td>
                        <div style="display:inline-flex; align-items:center; gap:6px; font-size:0.82rem;">
                            <span style="color:#64748b; font-weight:600;">Grupo ${s.grupo_actual}</span>
                            <i data-lucide="arrow-right" style="width:12px; height:12px; color:var(--primary);"></i>
                            <span style="color:#0369a1; font-weight:700; background:#e0f2fe; padding:0.15rem 0.4rem; border-radius:4px;">Grupo ${s.grupo_solicitado}</span>
                        </div>
                    </td>
                    <td style="font-size:0.78rem; color:#475569; max-width:180px;">
                        ${s.motivo || '<em>Sin motivo especificado</em>'}
                        ${s.respuesta_admin ? `<br><small style="color:#64748b;">(Dictamen: ${s.respuesta_admin})</small>` : ''}
                    </td>
                    <td>${badgeHtml}</td>
                    <td>${accionesHtml}</td>
                </tr>
            `;
        }).join('');

        UI.refrescarIconos();
    },

    async dictaminarSolicitud(id, accion) {
        if (accion === 'aprobar') {
            if (!confirm(`¿Confirma APROBAR la solicitud #${id}?\n\nSe ejecutará la reasignación oficial de grupo en la base de datos y se notificará internamente al estudiante.`)) return;
            try {
                const res = await API.aprobarSolicitud(id);
                UI.mostrarToast(res.mensaje, 'success');
                await this.cargarSolicitudesAdmin();
                this.cargarHorarios();
                this.cargarGrupos();
            } catch (err) {
                console.error("Error al aprobar solicitud:", err);
            }
        } else if (accion === 'rechazar') {
            const motivo = prompt(`Ingrese el motivo institucional del rechazo para la solicitud #${id} (se enviará como notificación al estudiante):`, "No cumple con criterios de aforo institucional o cruce de horario.");
            if (motivo === null) return;
            try {
                const res = await API.rechazarSolicitud(id, motivo);
                UI.mostrarToast(res.mensaje, 'warning');
                await this.cargarSolicitudesAdmin();
            } catch (err) {
                console.error("Error al rechazar solicitud:", err);
            }
        }
    },

    async cargarUsuariosAuth() {
        try {
            const users = await API.getAuthUsers();
            const tbodyUsers = document.getElementById('tbody-auth-users');
            if (tbodyUsers) {
                if (users.length === 0) {
                    tbodyUsers.innerHTML = '<tr><td colspan="9" style="text-align:center; padding:1.5rem; color:#64748b;">No hay usuarios registrados. Registre la primera cuenta arriba.</td></tr>';
                } else {
                    tbodyUsers.innerHTML = users.map(u => {
                        let roleBadge = '<span class="badge" style="background:#e0e7ff; color:#3730a3; border:1px solid #c7d2fe;">Usuario</span>';
                        if (u.role === 'admin') roleBadge = '<span class="badge badge-activo">Administrador</span>';
                        else if (u.role === 'teacher') roleBadge = '<span class="badge" style="background:#dbeafe; color:#1e40af; border:1px solid #bfdbfe;">Docente</span>';
                        else if (u.role === 'student') roleBadge = '<span class="badge" style="background:#fef3c7; color:#92400e; border:1px solid #fde68a;">Estudiante</span>';

                        const estadoHtml = u.is_active 
                            ? '<span style="color:#047857; font-weight:700;">● Activa</span>'
                            : '<span style="color:#b91c1c; font-weight:700;">● Inactiva</span>';

                        return `
                            <tr>
                                <td><strong>#${u.id}</strong></td>
                                <td>
                                    <strong>${u.nombre || u.username}</strong>
                                    <div style="font-size:0.75rem; color:#64748b;">@${u.username}</div>
                                </td>
                                <td><code>${u.documento || '—'}</code></td>
                                <td><code>${u.email}</code></td>
                                <td>
                                    ${roleBadge}
                                    <div style="font-size:0.74rem; color:#475569; margin-top:0.25rem;">${u.detalle_academico || ''}</div>
                                </td>
                                <td>${estadoHtml}</td>
                                <td style="text-align:center;">
                                    ${u.failed_attempts} / 3
                                    ${u.locked_until ? `<div style="font-size:0.7rem; color:#dc2626;">Bloqueado</div>` : ''}
                                </td>
                                <td style="font-size:0.75rem; color:#64748b;">${u.created_at ? u.created_at.split('T')[0] : '—'}</td>
                                <td style="text-align:center;">
                                    <button class="btn btn-sm btn-outline-danger" onclick="Controller.eliminarUsuarioAuth(${u.id}, '${u.username}')" style="padding:0.25rem 0.5rem; font-size:0.75rem;" title="Eliminar Usuario">
                                        <i data-lucide="trash-2" style="width:13px; height:13px;"></i>
                                    </button>
                                </td>
                            </tr>
                        `;
                    }).join('');
                }
            }

            const history = await API.getAuthLoginHistory();
            const tbodyHistory = document.getElementById('tbody-auth-login-history');
            if (tbodyHistory) {
                if (history.length === 0) {
                    tbodyHistory.innerHTML = '<tr><td colspan="7" style="text-align:center; padding:1.5rem; color:#64748b;">Sin eventos registrados en login_history.</td></tr>';
                } else {
                    tbodyHistory.innerHTML = history.map(h => {
                        const resBadge = h.success 
                            ? '<span class="badge badge-activo">ÉXITO</span>'
                            : '<span class="badge badge-riesgo">FALLIDO</span>';

                        return `
                            <tr>
                                <td>#${h.id}</td>
                                <td><strong>${h.username_attempted || '—'}</strong></td>
                                <td>${resBadge}</td>
                                <td style="font-size:0.78rem; color:#991b1b;">${h.failure_reason || '—'}</td>
                                <td style="font-size:0.75rem; color:#64748b;"><code>${h.ip_address || '127.0.0.1'}</code></td>
                                <td style="font-size:0.72rem; color:#64748b; max-width:200px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;" title="${h.user_agent}">${h.user_agent || 'Navegador'}</td>
                                <td style="font-size:0.78rem; color:#475569;">${h.login_at ? h.login_at.replace('T', ' ').split('.')[0] : '—'}</td>
                            </tr>
                        `;
                    }).join('');
                }
            }

            UI.refrescarIconos();
        } catch (err) {
            console.error("Error al cargar usuarios auth:", err);
        }
    },

    async eliminarUsuarioAuth(id, username) {
        if (!confirm(`¿Confirma eliminar la cuenta del usuario '${username}' (ID #${id}) de la base de datos?`)) return;
        try {
            const res = await API.eliminarAuthUser(id);
            UI.mostrarToast(res.mensaje, 'success');
            await this.cargarUsuariosAuth();
        } catch (err) {
            console.error("Error al eliminar usuario auth:", err);
        }
    },

    debounce(func, wait) {
        let timeout;
        return function(...args) {
            clearTimeout(timeout);
            timeout = setTimeout(() => func.apply(this, args), wait);
        };
    }
};


document.addEventListener('DOMContentLoaded', () => Controller.init());
