import sqlite3

def generar_sql_mysql():
    conn = sqlite3.connect('universidad.db')
    conn.row_factory = sqlite3.Row

    sql_lines = []
    sql_lines.append('-- =============================================================================')
    sql_lines.append('-- MIGRACIÓN DE BASE DE DATOS: SQLITE A MYSQL')
    sql_lines.append('-- Proyecto: UniGestion PRO - Sistema de Gestión Académica Universitario')
    sql_lines.append('-- Compatible con MySQL 5.7+ / MySQL 8.0+ / MariaDB 10.3+')
    sql_lines.append('-- =============================================================================\n')

    sql_lines.append('CREATE DATABASE IF NOT EXISTS `universidad_db` DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;')
    sql_lines.append('USE `universidad_db`;\n')

    sql_lines.append('SET FOREIGN_KEY_CHECKS = 0;\n')

    # 1. TABLA CARRERAS
    sql_lines.append('-- -----------------------------------------------------------------------------')
    sql_lines.append('-- 1. TABLA: carreras')
    sql_lines.append('-- -----------------------------------------------------------------------------')
    sql_lines.append('DROP TABLE IF EXISTS `carreras`;')
    sql_lines.append('''CREATE TABLE `carreras` (
  `id` VARCHAR(10) NOT NULL,
  `nombre` VARCHAR(100) NOT NULL,
  `codigo` VARCHAR(20) NOT NULL,
  `duracion_semestres` INT NOT NULL,
  `total_creditos` INT NOT NULL,
  `cupos_maximos` INT NOT NULL DEFAULT 30,
  `color` VARCHAR(20) NOT NULL,
  `descripcion` TEXT NOT NULL,
  `icono` VARCHAR(50) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_carreras_codigo` (`codigo`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;\n''')

    carreras = conn.execute('SELECT * FROM carreras;').fetchall()
    for c in carreras:
        vals = []
        for k, v in dict(c).items():
            if v is None:
                vals.append('NULL')
            elif isinstance(v, (int, float)):
                vals.append(str(v))
            else:
                s_escaped = str(v).replace("'", "\\'")
                vals.append(f"'{s_escaped}'")
        sql_lines.append(f"INSERT INTO `carreras` VALUES ({', '.join(vals)});")

    # 2. TABLA PROFESORES
    sql_lines.append('\n-- -----------------------------------------------------------------------------')
    sql_lines.append('-- 2. TABLA: profesores')
    sql_lines.append('-- -----------------------------------------------------------------------------')
    sql_lines.append('DROP TABLE IF EXISTS `profesores`;')
    sql_lines.append('''CREATE TABLE `profesores` (
  `id` VARCHAR(20) NOT NULL,
  `documento` VARCHAR(20) NOT NULL,
  `nombre` VARCHAR(100) NOT NULL,
  `email` VARCHAR(100) NOT NULL,
  `telefono` VARCHAR(30) NOT NULL,
  `titulo_academico` VARCHAR(100) NOT NULL,
  `carrera_principal` VARCHAR(10) NOT NULL,
  `estado` VARCHAR(20) NOT NULL DEFAULT 'Activo',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_profesores_documento` (`documento`),
  UNIQUE KEY `uk_profesores_email` (`email`),
  CONSTRAINT `fk_profesores_carrera` FOREIGN KEY (`carrera_principal`) REFERENCES `carreras` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;\n''')

    profesores = conn.execute('SELECT * FROM profesores;').fetchall()
    for p in profesores:
        vals = []
        for k, v in dict(p).items():
            if v is None:
                vals.append('NULL')
            elif isinstance(v, (int, float)):
                vals.append(str(v))
            else:
                s_escaped = str(v).replace("'", "\\'")
                vals.append(f"'{s_escaped}'")
        sql_lines.append(f"INSERT INTO `profesores` VALUES ({', '.join(vals)});")

    # 3. TABLA ASIGNATURAS
    sql_lines.append('\n-- -----------------------------------------------------------------------------')
    sql_lines.append('-- 3. TABLA: asignaturas')
    sql_lines.append('-- -----------------------------------------------------------------------------')
    sql_lines.append('DROP TABLE IF EXISTS `asignaturas`;')
    sql_lines.append('''CREATE TABLE `asignaturas` (
  `id` VARCHAR(20) NOT NULL,
  `codigo` VARCHAR(20) NOT NULL,
  `nombre` VARCHAR(150) NOT NULL,
  `creditos` INT NOT NULL,
  `nivel` INT NOT NULL CHECK (`nivel` IN (1, 2, 3)),
  `tipo` VARCHAR(20) NOT NULL CHECK (`tipo` IN ('exclusiva', 'compartida')),
  `carrera_id` VARCHAR(10) DEFAULT NULL,
  `carreras_compartidas` VARCHAR(100) DEFAULT NULL,
  `docente` VARCHAR(100) NOT NULL,
  `horario` VARCHAR(50) NOT NULL,
  `grupo` VARCHAR(10) NOT NULL DEFAULT 'G1',
  `aula` VARCHAR(50) NOT NULL DEFAULT 'Aula 101',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_asignaturas_codigo` (`codigo`),
  CONSTRAINT `fk_asignaturas_carrera` FOREIGN KEY (`carrera_id`) REFERENCES `carreras` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;\n''')

    asignaturas = conn.execute('SELECT * FROM asignaturas;').fetchall()
    for a in asignaturas:
        vals = []
        for k, v in dict(a).items():
            if v is None:
                vals.append('NULL')
            elif isinstance(v, (int, float)):
                vals.append(str(v))
            else:
                s_escaped = str(v).replace("'", "\\'")
                vals.append(f"'{s_escaped}'")
        sql_lines.append(f"INSERT INTO `asignaturas` VALUES ({', '.join(vals)});")

    # 4. TABLA ESTUDIANTES
    sql_lines.append('\n-- -----------------------------------------------------------------------------')
    sql_lines.append('-- 4. TABLA: estudiantes')
    sql_lines.append('-- -----------------------------------------------------------------------------')
    sql_lines.append('DROP TABLE IF EXISTS `estudiantes`;')
    sql_lines.append('''CREATE TABLE `estudiantes` (
  `id` VARCHAR(20) NOT NULL,
  `matricula` VARCHAR(30) NOT NULL,
  `nombre` VARCHAR(100) NOT NULL,
  `email` VARCHAR(100) NOT NULL,
  `telefono` VARCHAR(30) NOT NULL,
  `carrera_id` VARCHAR(10) NOT NULL,
  `semestre` INT NOT NULL CHECK (`semestre` BETWEEN 1 AND 10),
  `estado` VARCHAR(20) NOT NULL CHECK (`estado` IN ('Activo', 'En Riesgo', 'Egresado', 'Suspendido')),
  `estado_pago` VARCHAR(20) NOT NULL DEFAULT 'Al día' CHECK (`estado_pago` IN ('Al día', 'Pendiente', 'Bloqueado')),
  `promedio` DOUBLE NOT NULL DEFAULT 0.0,
  `foto_avatar` VARCHAR(255) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_estudiantes_matricula` (`matricula`),
  CONSTRAINT `fk_estudiantes_carrera` FOREIGN KEY (`carrera_id`) REFERENCES `carreras` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;\n''')

    estudiantes = conn.execute('SELECT * FROM estudiantes;').fetchall()
    for e in estudiantes:
        vals = []
        for k, v in dict(e).items():
            if v is None:
                vals.append('NULL')
            elif isinstance(v, (int, float)):
                vals.append(str(v))
            else:
                s_escaped = str(v).replace("'", "\\'")
                vals.append(f"'{s_escaped}'")
        sql_lines.append(f"INSERT INTO `estudiantes` VALUES ({', '.join(vals)});")

    # 5. TABLA INSCRIPCIONES
    sql_lines.append('\n-- -----------------------------------------------------------------------------')
    sql_lines.append('-- 5. TABLA: inscripciones')
    sql_lines.append('-- -----------------------------------------------------------------------------')
    sql_lines.append('DROP TABLE IF EXISTS `inscripciones`;')
    sql_lines.append('''CREATE TABLE `inscripciones` (
  `id` INT AUTO_INCREMENT NOT NULL,
  `estudiante_id` VARCHAR(20) NOT NULL,
  `asignatura_id` VARCHAR(20) NOT NULL,
  `nota` DOUBLE NOT NULL CHECK (`nota` BETWEEN 0.0 AND 5.0),
  `periodo` VARCHAR(20) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_estudiante_asignatura` (`estudiante_id`, `asignatura_id`),
  CONSTRAINT `fk_inscripciones_estudiante` FOREIGN KEY (`estudiante_id`) REFERENCES `estudiantes` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_inscripciones_asignatura` FOREIGN KEY (`asignatura_id`) REFERENCES `asignaturas` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;\n''')

    inscripciones = conn.execute('SELECT * FROM inscripciones;').fetchall()
    for i in inscripciones:
        vals = []
        for k, v in dict(i).items():
            if v is None:
                vals.append('NULL')
            elif isinstance(v, (int, float)):
                vals.append(str(v))
            else:
                s_escaped = str(v).replace("'", "\\'")
                vals.append(f"'{s_escaped}'")
        sql_lines.append(f"INSERT INTO `inscripciones` VALUES ({', '.join(vals)});")

    # 6. TABLA NOTIFICACIONES
    sql_lines.append('\n-- -----------------------------------------------------------------------------')
    sql_lines.append('-- 6. TABLA: notificaciones')
    sql_lines.append('-- -----------------------------------------------------------------------------')
    sql_lines.append('DROP TABLE IF EXISTS `notificaciones`;')
    sql_lines.append('''CREATE TABLE `notificaciones` (
  `id` INT AUTO_INCREMENT NOT NULL,
  `estudiante_id` VARCHAR(20) NOT NULL,
  `titulo` VARCHAR(150) NOT NULL,
  `mensaje` TEXT NOT NULL,
  `tipo` VARCHAR(20) NOT NULL DEFAULT 'pago' CHECK (`tipo` IN ('pago', 'academico', 'sistema')),
  `fecha` VARCHAR(30) NOT NULL,
  `leido` TINYINT(1) NOT NULL DEFAULT 0,
  PRIMARY KEY (`id`),
  CONSTRAINT `fk_notificaciones_estudiante` FOREIGN KEY (`estudiante_id`) REFERENCES `estudiantes` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;\n''')

    notificaciones = conn.execute('SELECT * FROM notificaciones;').fetchall()
    for n in notificaciones:
        vals = []
        for k, v in dict(n).items():
            if v is None:
                vals.append('NULL')
            elif isinstance(v, (int, float)):
                vals.append(str(v))
            else:
                s_escaped = str(v).replace("'", "\\'")
                vals.append(f"'{s_escaped}'")
        sql_lines.append(f"INSERT INTO `notificaciones` VALUES ({', '.join(vals)});")

    sql_lines.append('\nSET FOREIGN_KEY_CHECKS = 1;\n')
    sql_lines.append('-- =============================================================================')
    sql_lines.append('-- FIN DEL SCRIPT DE MIGRACIÓN MYSQL')
    sql_lines.append('-- Total: 3 carreras, 20 profesores, 52 asignaturas, 80 estudiantes.')
    sql_lines.append('-- =============================================================================')

    with open('migracion_mysql.sql', 'w', encoding='utf-8') as f:
        f.write('\n'.join(sql_lines))

    print('[OK] Script migracion_mysql.sql generado exitosamente.')

if __name__ == '__main__':
    generar_sql_mysql()
