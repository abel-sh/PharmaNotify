#!/bin/bash
# src/scripts/init_db.sh
#
# Script de inicialización de la base de datos.
# Lee la configuración desde el archivo .env ubicado en final/.
# Crea las tablas necesarias para el sistema de notificaciones.
#
# Uso: bash scripts/init_db.sh  (ejecutar desde el directorio final/)

# =============================================================================
# Cargar variables desde .env
# =============================================================================

# dirname "$0" devuelve el directorio donde está este script (scripts/).
# Desde ahí subimos un nivel con /.. para llegar a final/, donde vive el .env.
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
#
# La sintaxis ${VARIABLE:-default} significa: "usá el valor de VARIABLE si
# existe y no está vacía, de lo contrario usá default". Es la forma bash de
# hacer lo mismo que os.getenv("VARIABLE", "default") en Python.
# =============================================================================
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-3306}"
DB_NAME="${DB_NAME:-pharma_db}"
DB_USER="${DB_USER:-pharma_user}"
DB_PASS="${DB_PASSWORD:-pharma_pass}"  # En bash usamos DB_PASS como nombre local
                                       # para no pisar la variable DB_PASSWORD del entorno

# =============================================================================
# Verificar que el cliente mysql está disponible en el sistema
# =============================================================================

# 'command -v mysql' devuelve la ruta del ejecutable si existe, o nada si no.
# El '!' niega el resultado: si mysql NO está disponible, entramos al if.
if ! command -v mysql &> /dev/null; then
    echo "Error: el cliente 'mysql' no está instalado o no está en el PATH."
    exit 1
fi

# =============================================================================
# Función auxiliar para ejecutar SQL y reportar el resultado
# =============================================================================
ejecutar_sql() {
    local descripcion="$1"  # Primer argumento: nombre legible de la operación
    local sql="$2"           # Segundo argumento: la sentencia SQL a ejecutar

    # Pasamos el SQL directamente al cliente mysql con -e (execute).
    # El 2>&1 redirige los errores de stderr a stdout para poder capturarlos.
    mysql -h "$DB_HOST" -P "$DB_PORT" -u "$DB_USER" -p"$DB_PASS" "$DB_NAME" -e "$sql" 2>&1

    # $? es el código de salida del último comando ejecutado.
    # 0 significa éxito; cualquier otro valor indica un error.
    if [ $? -eq 0 ]; then
        echo "  ✓ $descripcion"
    else
        echo "  ✗ Error al crear: $descripcion"
        echo "  Abortando inicialización."
        exit 1  # Detenemos el script inmediatamente ante cualquier falla
    fi
}

# =============================================================================
# Inicio del proceso
# =============================================================================
echo ""
echo "Conectando a MariaDB en ${DB_HOST}:${DB_PORT}..."
echo "Inicializando base de datos '${DB_NAME}'..."
echo ""

ejecutar_sql "Tabla 'farmacias'" "
    CREATE TABLE IF NOT EXISTS farmacias (
        id          INT AUTO_INCREMENT PRIMARY KEY,
        nombre      VARCHAR(100) NOT NULL UNIQUE,
        umbral_dias INT NOT NULL DEFAULT 7,
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