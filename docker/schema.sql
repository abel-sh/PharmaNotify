-- =============================================================================
-- docker/init_db.sql
--
-- Inicialización de tablas para PharmaNotify.
--
-- Este archivo es ejecutado automáticamente por el contenedor de MariaDB
-- la PRIMERA vez que arranca con un volumen vacío, gracias al mecanismo
-- de /docker-entrypoint-initdb.d/. Si el volumen ya tiene datos (es decir,
-- ya se inicializó antes), este script NO se vuelve a ejecutar.
--
-- El usuario y la base de datos ya fueron creados por las variables de entorno
-- MYSQL_DATABASE, MYSQL_USER y MYSQL_PASSWORD definidas en docker-compose.yml.
-- Este script solo necesita seleccionar esa base de datos y crear las tablas.
-- =============================================================================

USE pharma_db;

-- -----------------------------------------------------------------------------
-- Tabla: farmacias
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS farmacias (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    nombre      VARCHAR(100) NOT NULL UNIQUE,
    umbral_dias INT NOT NULL DEFAULT 7,
    activo      BOOLEAN NOT NULL DEFAULT TRUE,
    creado_en   DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- -----------------------------------------------------------------------------
-- Tabla: medicamentos
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS medicamentos (
    id                INT AUTO_INCREMENT PRIMARY KEY,
    farmacia_id       INT NOT NULL,
    codigo            VARCHAR(50) NOT NULL,
    nombre            VARCHAR(100) NOT NULL,
    fecha_vencimiento DATE NOT NULL,
    activo            BOOLEAN DEFAULT TRUE,
    motivo_baja       ENUM('eliminado_manual', 'vencido_automatico') DEFAULT NULL,
    creado_en         TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (farmacia_id) REFERENCES farmacias(id),
    UNIQUE (farmacia_id, codigo)
);

-- -----------------------------------------------------------------------------
-- Tabla: notificaciones
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS notificaciones (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    farmacia_id INT NOT NULL,
    tipo        VARCHAR(50) NOT NULL,
    mensaje     TEXT NOT NULL,
    leida       BOOLEAN NOT NULL DEFAULT FALSE,
    creado_en   DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (farmacia_id) REFERENCES farmacias(id)
);