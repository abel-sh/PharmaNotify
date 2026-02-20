#!/bin/bash
# src/scripts/init_db.sh
#
# Script de inicialización de la base de datos.
# Lee la configuración desde el archivo .env ubicado en final/.
# Crea la base de datos y las tablas necesarias para el sistema de notificaciones.
#
# Uso: bash scripts/init_db.sh  (ejecutar desde el directorio final/)

# =============================================================================
# Cargar variables desde .env
# =============================================================================

ENV_FILE="$(dirname "$0")/../.env"

if [ -f "$ENV_FILE" ]; then
    source "$ENV_FILE"
    echo "Configuración cargada desde .env"
else
    echo "Advertencia: no se encontró el archivo .env en $(dirname "$0")/.."
    echo "Se usarán los valores por defecto."
fi

# =============================================================================
# Configuración con valores por defecto
# =============================================================================
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-3306}"
DB_NAME="${DB_NAME:-pharma_db}"
DB_USER="${DB_USER:-pharma_user}"
DB_PASS="${DB_PASSWORD:-pharma_pass}"

# =============================================================================
# Verificar que el cliente mysql está disponible en el sistema
# =============================================================================

if ! command -v mysql &> /dev/null; then
    echo "Error: el cliente 'mysql' no está instalado o no está en el PATH."
    exit 1
fi

# =============================================================================
# FASE 1: Crear la base de datos si no existe
# =============================================================================
echo ""
echo "Conectando a MariaDB en ${DB_HOST}:${DB_PORT}..."
echo ""

# Acá nos conectamos SIN especificar ninguna base de datos (sin el parámetro $DB_NAME)
# Solo nos autenticamos con usuario y contraseña, y ejecutamos el CREATE DATABASE
echo "Creando base de datos '${DB_NAME}' si no existe..."
mysql -h "$DB_HOST" -P "$DB_PORT" -u "$DB_USER" -p"$DB_PASS" -e "CREATE DATABASE IF NOT EXISTS ${DB_NAME};" 2>&1

if [ $? -eq 0 ]; then
    echo "  ✓ Base de datos '${DB_NAME}' lista"
else
    echo "  ✗ Error al crear la base de datos"
    echo "  Verificá las credenciales y que el usuario tenga permisos para crear bases de datos."
    exit 1
fi

# =============================================================================
# FASE 2: Crear las tablas dentro de la base de datos
# =============================================================================
echo ""
echo "Inicializando tablas en '${DB_NAME}'..."
echo ""

# Función auxiliar para ejecutar SQL y reportar el resultado
# AHORA sí especificamos $DB_NAME porque ya sabemos que existe
ejecutar_sql() {
    local descripcion="$1"
    local sql="$2"

    mysql -h "$DB_HOST" -P "$DB_PORT" -u "$DB_USER" -p"$DB_PASS" "$DB_NAME" -e "$sql" 2>&1

    if [ $? -eq 0 ]; then
        echo "  ✓ $descripcion"
    else
        echo "  ✗ Error al crear: $descripcion"
        echo "  Abortando inicialización."
        exit 1
    fi
}

ejecutar_sql "Tabla 'farmacias'" "
    CREATE TABLE IF NOT EXISTS farmacias (
        id          INT AUTO_INCREMENT PRIMARY KEY,
        nombre      VARCHAR(100) NOT NULL UNIQUE,
        umbral_dias INT NOT NULL DEFAULT 7,
        activo      BOOLEAN NOT NULL DEFAULT TRUE,
        creado_en   DATETIME DEFAULT CURRENT_TIMESTAMP
    );
"

ejecutar_sql "Tabla 'medicamentos'" "
    CREATE TABLE IF NOT EXISTS medicamentos (
        id                INT AUTO_INCREMENT PRIMARY KEY,
        farmacia_id       INT NOT NULL,
        codigo            VARCHAR(50) NOT NULL,
        nombre            VARCHAR(150) NOT NULL,
        fecha_vencimiento DATE NOT NULL,
        activo            BOOLEAN NOT NULL DEFAULT TRUE,
        creado_en         DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (farmacia_id) REFERENCES farmacias(id),
        UNIQUE KEY uq_farmacia_codigo (farmacia_id, codigo)
    );
"

ejecutar_sql "Tabla 'notificaciones'" "
    CREATE TABLE IF NOT EXISTS notificaciones (
        id          INT AUTO_INCREMENT PRIMARY KEY,
        farmacia_id INT NOT NULL,
        tipo        VARCHAR(50) NOT NULL,
        mensaje     TEXT NOT NULL,
        leida       BOOLEAN NOT NULL DEFAULT FALSE,
        creado_en   DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (farmacia_id) REFERENCES farmacias(id)
    );
"

echo ""
echo "Base de datos inicializada correctamente."
echo "Podés verificar las tablas con:"
echo "  mysql -u $DB_USER -p $DB_NAME -e 'SHOW TABLES;'"