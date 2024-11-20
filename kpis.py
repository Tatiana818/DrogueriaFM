import sqlite3

def crear_tablas():
    # Usar un contexto para asegurar que la conexión se cierre automáticamente
    with sqlite3.connect('cadena_suministro.db') as conn:
        cursor = conn.cursor()

        # Eliminar tablas si existen para evitar errores de duplicación
        tablas = ['indicadores_residuos', 'indicadores_logistica', 'indicador_reclamos']
        for tabla in tablas:
            cursor.execute(f'DROP TABLE IF EXISTS {tabla}')

        # Crear tabla para los indicadores de residuos
        cursor.execute('''  
            CREATE TABLE indicadores_residuos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                mes_anterior TEXT NOT NULL,
                residuos_anterior REAL NOT NULL,
                mes_actual TEXT NOT NULL,
                residuos_actual REAL NOT NULL,
                resultado REAL NOT NULL,
                fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Crear tabla para los indicadores de logística de compras
        cursor.execute(''' 
            CREATE TABLE indicadores_logistica (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                proveedor TEXT NOT NULL,
                cantidad_recibida REAL NOT NULL,
                cantidad_solicitada REAL NOT NULL,
                resultado REAL NOT NULL,
                fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Crear la tabla indicador_reclamos
        cursor.execute(''' 
            CREATE TABLE IF NOT EXISTS indicador_reclamos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                mes TEXT NOT NULL,
                cantidad_reclamos INTEGER NOT NULL,
                cantidad_clientes INTEGER NOT NULL,
                porcentaje_reclamos REAL NOT NULL,               -- Porcentaje de reclamos sobre clientes
                resultado TEXT NOT NULL,                -- Resultado de evaluación, p.ej., "Crítico", "Riesgo", "Adecuado"
                color TEXT NOT NULL,                    -- Color asociado al resultado, p.ej., "Rojo", "Amarillo", "Verde"
                fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Crear tabla para el indicador de rotación de inventarios
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS indicador_rotacion (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                producto TEXT NOT NULL,
                inventario_inicial REAL NOT NULL,
                inventario_final REAL NOT NULL,
                ventas REAL NOT NULL,
                rotacion REAL NOT NULL,
                fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Confirmar los cambios en la base de datos
        conn.commit()
        print("Tablas creadas exitosamente.")  # Mensaje de confirmación

if __name__ == '__main__':
    crear_tablas()  # Ejecuta la función para crear las tablas
