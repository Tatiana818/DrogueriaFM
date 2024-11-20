import sqlite3
import pandas as pd

# Conexión a la base de datos
conn = sqlite3.connect('cadena_suministro.db')
cursor = conn.cursor()

# Eliminar la tabla 'inventario' si ya existe para crearla de nuevo
cursor.execute('DROP TABLE IF EXISTS inventario')

# Crear tabla para inventario (con columnas adicionales)
cursor.execute('''
CREATE TABLE IF NOT EXISTS inventario (
    id_producto INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre_producto TEXT NOT NULL,
    proveedor TEXT,
    cantidad INTEGER,
    precio_unitario REAL,
    fecha_expiracion DATE,
    demanda_estimada_diaria REAL,  -- Columna de demanda estimada
    tiempo_entrega INTEGER,         -- Nueva columna para el tiempo de entrega en días
    umbral_seguridad INTEGER        -- Nueva columna para el nivel de seguridad
)
''')
conn.commit()

# Leer el archivo CSV con pandas e insertar los datos en la tabla 'inventario'
inventario_data = pd.read_csv('inventario.csv', delimiter=';')

# Insertar los datos del CSV en la tabla 'inventario', incluyendo la nueva columna de tiempo de entrega y umbral de seguridad
for index, row in inventario_data.iterrows():
    cursor.execute('''
        INSERT INTO inventario (nombre_producto, proveedor, cantidad, precio_unitario, fecha_expiracion, demanda_estimada_diaria, tiempo_entrega, umbral_seguridad)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (row['nombre_producto'], row['proveedor'], row['cantidad'], row['precio_unitario'], row['fecha_expiracion'], row['demanda_estimada_diaria'], row['tiempo_entrega'], row['umbral_seguridad']))

# Guardar los cambios y cerrar la conexión temporal
conn.commit()

import sqlite3

# Crear base de datos y tablas si no existen
def inicializar_db():
    with sqlite3.connect('cadena_suministro.db') as conn:
        cursor = conn.cursor()
        
        # Crear tabla de inventario si no existe
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS inventario (
            id_producto INTEGER PRIMARY KEY,
            nombre_producto TEXT,
            cantidad INTEGER,
            precio_unitario REAL,
            demanda_estimada_diaria REAL
        )
        ''')

        # Crear tabla de ventas si no existe
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS ventas (
            id_venta INTEGER PRIMARY KEY AUTOINCREMENT,
            id_producto INTEGER,
            nombre_producto TEXT,
            cantidad_vendida INTEGER,
            valor_total REAL,
            fecha_venta TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (id_producto) REFERENCES inventario (id_producto)
        )
        ''')

        conn.commit()

# Llama a la función para crear las tablas
inicializar_db()

# Registrar ventas y actualizar inventario y demanda estimada
def registrar_venta(id_producto, cantidad_vendida):
    conn = sqlite3.connect('cadena_suministro.db')
    cursor = conn.cursor()

    # Actualizar inventario restando la cantidad vendida
    cursor.execute('''
    UPDATE inventario SET cantidad = cantidad - ? WHERE id_producto = ?
    ''', (cantidad_vendida, id_producto))

    # Obtener demanda estimada y recalcular según las ventas
    cursor.execute('SELECT demanda_estimada_diaria, cantidad FROM inventario WHERE id_producto = ?', (id_producto,))
    resultado = cursor.fetchone()
    demanda_estimada = resultado[0]
    stock_actual = resultado[1]

    # Actualizar la demanda estimada como promedio con la venta actual
    nueva_demanda_estimada = (demanda_estimada + (cantidad_vendida / 30)) / 2
    
    cursor.execute('''
    UPDATE inventario SET demanda_estimada_diaria = ? WHERE id_producto = ?
    ''', (nueva_demanda_estimada, id_producto))

    conn.commit()
    conn.close()

# Verificar si es necesario reabastecer según nivel de seguridad
def verificar_reabastecimiento():
    conn = sqlite3.connect('cadena_suministro.db')
    cursor = conn.cursor()

    cursor.execute('SELECT nombre_producto, cantidad, umbral_seguridad FROM inventario WHERE cantidad < umbral_seguridad')
    productos_bajos = cursor.fetchall()
    conn.close()

    if productos_bajos:
        for producto in productos_bajos:
            print(f"Reabastecer: {producto[0]}, cantidad actual: {producto[1]}, umbral de seguridad: {producto[2]}")
    else:
        print("Todos los productos están por encima del nivel de seguridad.")

# MRP según demanda estimada y lead time
def calcular_mrp(id_producto):
    conn = sqlite3.connect('cadena_suministro.db')
    cursor = conn.cursor()

    cursor.execute('SELECT cantidad, demanda_estimada_diaria, tiempo_entrega, umbral_seguridad FROM inventario WHERE id_producto = ?', (id_producto,))
    resultado = cursor.fetchone()
    stock_actual = resultado[0]
    demanda_estimada_diaria = resultado[1]
    tiempo_entrega = resultado[2]
    umbral_seguridad = resultado[3]

    # Calcular requerimiento con nivel de seguridad
    requerimiento = demanda_estimada_diaria * tiempo_entrega + umbral_seguridad

    if stock_actual < requerimiento:
        print(f"Se debe realizar un pedido para el producto con ID {id_producto}.")
    else:
        print(f"Stock suficiente para el producto con ID {id_producto}.")

# Indicadores de sostenibilidad
def tasa_residuos(total_residuos, total_ventas):
    return total_residuos / total_ventas

def porcentaje_reduccion_residuos(residuos_pasado, residuos_presente):
    return (residuos_pasado - residuos_presente) / residuos_pasado * 100

# Ejemplo para mostrar el número de productos en inventario
conn = sqlite3.connect('cadena_suministro.db')
cursor = conn.cursor()
cursor.execute("SELECT COUNT(*) FROM inventario")
count = cursor.fetchone()[0]
print(f"Productos en inventario: {count}")
conn.close()
