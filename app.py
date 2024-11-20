from flask import Flask, flash, render_template, request, redirect, url_for, jsonify,send_from_directory,send_file
import sqlite3
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import base64
from io import BytesIO
import io
import numpy as np
import locale
import plotly.graph_objects as go
import plotly.io as pio
import plotly.graph_objs as go
from plotly.offline import plot
import plotly.express as px
import os
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
from datetime import datetime
from reportlab.lib.units import inch
from reportlab.lib import colors
import pandas as pd
import sqlite3
from statsmodels.tsa.arima.model import ARIMA
import json
import plotly

app = Flask(__name__)
# Ruta para la página principal
@app.route('/')
def inicio():
    return render_template('index.html')

# Ruta para mostrar inventario
@app.route('/inventario')
def mostrar_inventario():
    conn = sqlite3.connect('cadena_suministro.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM inventario")
    inventario = cursor.fetchall()

    # Verificar productos con cantidades por debajo del umbral de seguridad
    cursor.execute('SELECT nombre_producto FROM inventario WHERE cantidad < umbral_seguridad')
    productos_bajos = cursor.fetchall()
    conn.close()
    
    return render_template('inventario.html', inventario=inventario, productos_bajos=productos_bajos)

# Ruta para agregar un nuevo producto
@app.route('/agregar_producto', methods=['GET', 'POST'])
def agregar_producto():
    if request.method == 'POST':
        nombre_producto = request.form['nombre_producto']
        proveedor = request.form['proveedor']
        cantidad = request.form['cantidad']
        precio_unitario = request.form['precio_unitario']
        fecha_expiracion = request.form['fecha_expiracion']
        demanda_estimada_diaria = request.form['demanda_estimada_diaria']
        tiempo_entrega = request.form['tiempo_entrega']
        umbral_seguridad = request.form['umbral_seguridad']  # Nuevo campo para el umbral de seguridad
        
        print(f"Producto a agregar: {nombre_producto}, Proveedor: {proveedor}, Cantidad: {cantidad}, Precio: {precio_unitario}, Fecha de Expiración: {fecha_expiracion}, Demanda Estimada Diaria: {demanda_estimada_diaria}, Tiempo de Entrega: {tiempo_entrega}, Umbral de Seguridad: {umbral_seguridad}")
        
        conn = sqlite3.connect('cadena_suministro.db')
        cursor = conn.cursor()

        try:
            cursor.execute('''INSERT INTO inventario 
                              (nombre_producto, proveedor, cantidad, precio_unitario, fecha_expiracion, demanda_estimada_diaria, tiempo_entrega, umbral_seguridad)
                              VALUES (?, ?, ?, ?, ?, ?, ?, ?)''', 
                           (nombre_producto, proveedor, cantidad, precio_unitario, fecha_expiracion, demanda_estimada_diaria, tiempo_entrega, umbral_seguridad))
            conn.commit()
        except Exception as e:
            conn.rollback()
            print(f"Error al insertar los datos: {e}")
            return "Hubo un error al agregar el producto."
        finally:
            conn.close()
        
        return redirect(url_for('mostrar_inventario'))
    
    return render_template('agregar_producto.html')
# Ruta para eliminar un producto
@app.route('/eliminar_producto', methods=['POST'])
def eliminar_producto():
    producto_id = request.form['producto_id']  # Obtener el ID del producto del formulario

    conn = sqlite3.connect('cadena_suministro.db')
    cursor = conn.cursor()

    try:
        cursor.execute('DELETE FROM inventario WHERE id_producto = ?', (producto_id,))
        conn.commit()
        print(f"Producto con ID {producto_id} eliminado.")
    except Exception as e:
        conn.rollback()
        print(f"Error al eliminar el producto: {e}")
        return "Hubo un error al eliminar el producto."
    finally:
        conn.close()
    
    return redirect(url_for('mostrar_inventario'))  # Redirigir a la lista de inventario después de eliminar

######
@app.route('/registrar_venta', methods=['GET', 'POST'])
def registrar_venta():
    if request.method == 'POST':
        # Recibe datos del formulario
        productos_vendidos = request.form.getlist('id_producto')  # Lista de IDs de productos
        cantidades_vendidas = request.form.getlist('cantidad_vendida')  # Lista de cantidades vendidas
        desea_factura = request.form.get('factura')  # Verifica si se solicitó factura
        nombre_cliente = request.form.get('nombre_cliente', '')
        cedula_o_nit_cliente = request.form.get('cedula_o_nit_cliente', '')
        telefono_cliente = request.form.get('telefono_cliente', '')

        detalles_venta = []
        valor_total_venta = 0

        with sqlite3.connect('cadena_suministro.db') as conn:
            cursor = conn.cursor()

            for i in range(len(productos_vendidos)):
                id_producto = productos_vendidos[i]
                cantidad_vendida = int(cantidades_vendidas[i])

                # Validar que la cantidad sea positiva
                if cantidad_vendida <= 0:
                    return f"Error: Cantidad no válida para el producto ID {id_producto}"

                # Obtener detalles del producto
                cursor.execute("SELECT nombre_producto, precio_unitario, cantidad FROM inventario WHERE id_producto = ?", (id_producto,))
                producto = cursor.fetchone()
                if not producto:
                    return f"Error: Producto ID {id_producto} no encontrado."

                nombre_producto, precio_unitario, cantidad_disponible = producto

                # Verificar si hay suficiente inventario
                if cantidad_vendida > cantidad_disponible:
                    return f"Error: No hay suficiente inventario para el producto {nombre_producto}."

                # Calcular el valor total del producto y actualizar inventario
                valor_total_producto = cantidad_vendida * precio_unitario
                valor_total_venta += valor_total_producto
                cursor.execute("UPDATE inventario SET cantidad = cantidad - ? WHERE id_producto = ?", (cantidad_vendida, id_producto))

                # Agregar detalle de producto a la lista de ventas
                detalles_venta.append({
                    'id_producto': id_producto,
                    'nombre_producto': nombre_producto,
                    'cantidad_vendida': cantidad_vendida,
                    'precio_unitario': precio_unitario,
                    'valor_total_producto': valor_total_producto
                })

                # Registrar cada producto vendido en la tabla de ventas
                fecha_venta = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                cursor.execute("""
                    INSERT INTO ventas (id_producto, nombre_producto, cantidad_vendida, valor_total, fecha_venta)
                    VALUES (?, ?, ?, ?, ?)
                """, (id_producto, nombre_producto, cantidad_vendida, valor_total_producto, fecha_venta))

            conn.commit()

            # Obtener número de la factura
            cursor.execute("SELECT MAX(id_venta) FROM ventas")
            numero_factura = cursor.fetchone()[0]

        # Generar factura si se requiere
        if desea_factura:
            pdf_buffer = generar_factura_pdf(detalles_venta, valor_total_venta, fecha_venta, nombre_cliente, cedula_o_nit_cliente, telefono_cliente, numero_factura)
            return send_file(pdf_buffer, as_attachment=True, download_name="factura.pdf", mimetype='application/pdf')

        return redirect(url_for('historial_ventas'))

    # Si se accede con GET
    with sqlite3.connect('cadena_suministro.db') as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id_producto, nombre_producto FROM inventario")
        productos = cursor.fetchall()

    return render_template('registrar_venta.html', productos=productos)

def generar_factura_pdf(detalles_venta, valor_total_venta, fecha_venta, nombre_cliente, cedula_o_nit_cliente, telefono_cliente, numero_factura):
    # Ruta del logo
    logo_path = r"C:\Users\danim\Documents\Drogueria\Templates\Logo.png"
    
    # Crear buffer para el PDF
    pdf_buffer = io.BytesIO()
    pdf = canvas.Canvas(pdf_buffer, pagesize=letter)

    # Colores y estilos personalizados
    header_color = colors.HexColor("#1E90FF")
    text_color = colors.HexColor("#333333")
    background_color = colors.HexColor("#F4F4F4")
    line_color = colors.HexColor("#1E90FF")

    # Establecer márgenes
    margin_left = 40
    margin_top = 750

    # Fondo del documento
    pdf.setFillColor(background_color)
    pdf.rect(0, 0, 600, 850, fill=1)

    # Encabezado
    if os.path.exists(logo_path):
        pdf.drawImage(logo_path, margin_left, margin_top, width=100, height=40)
    pdf.setFont("Helvetica-Bold", 16)
    pdf.setFillColor(header_color)
    pdf.drawString(150, margin_top + 15, "Droguería Distrital FM")
    pdf.setFont("Helvetica", 10)
    pdf.setFillColor(text_color)
    pdf.drawString(150, margin_top - 10, "NIT: 79817470")
    pdf.drawString(150, margin_top - 25, "Tel: 3106348708 | william@hotmail.com")
    pdf.drawString(150, margin_top - 40, "Dirección: Calle 123, Bogotá")

    # Fecha y número de factura
    pdf.setFont("Helvetica-Bold", 12)
    pdf.setFillColor(header_color)
    pdf.drawString(400, margin_top - 30, f"Factura Nº: {numero_factura}")
    pdf.setFont("Helvetica", 10)
    pdf.setFillColor(text_color)
    pdf.drawString(400, margin_top - 45, f"Fecha de emisión: {fecha_venta}")

    # Datos del cliente
    pdf.setFont("Helvetica-Bold", 12)
    pdf.setFillColor(header_color)
    pdf.drawString(margin_left, margin_top - 90, "Cliente:")
    pdf.setFont("Helvetica", 10)
    pdf.setFillColor(text_color)
    pdf.drawString(margin_left, margin_top - 105, f"Nombre: {nombre_cliente}")
    pdf.drawString(margin_left, margin_top - 120, f"Cédula o NIT: {cedula_o_nit_cliente}")
    pdf.drawString(margin_left, margin_top - 135, f"Teléfono: {telefono_cliente}")

    # Tabla de productos vendidos
    pdf.setFont("Helvetica-Bold", 10)
    pdf.setFillColor(header_color)
    pdf.drawString(margin_left, margin_top - 165, "Descripción del Producto")
    pdf.drawString(margin_left + 200, margin_top - 165, "Cantidad")
    pdf.drawString(margin_left + 300, margin_top - 165, "Precio Unitario")
    pdf.drawString(margin_left + 400, margin_top - 165, "Valor Total")
    pdf.setStrokeColor(line_color)
    pdf.line(margin_left, margin_top - 170, 570, margin_top - 170)

    # Detalles de los productos
    y_position = margin_top - 190
    pdf.setFont("Helvetica", 10)
    pdf.setFillColor(text_color)

    for detalle in detalles_venta:
        pdf.drawString(margin_left, y_position, detalle['nombre_producto'])
        pdf.drawString(margin_left + 200, y_position, str(detalle['cantidad_vendida']))
        pdf.drawString(margin_left + 300, y_position, f"${detalle['precio_unitario']:,.2f}")
        pdf.drawString(margin_left + 400, y_position, f"${detalle['valor_total_producto']:,.2f}")
        y_position -= 20

    # Resumen de la venta
    iva = valor_total_venta * 0.19
    total = valor_total_venta + iva
    y_position -= 40

    pdf.setFont("Helvetica-Bold", 12)
    pdf.setFillColor(header_color)
    pdf.drawString(margin_left, y_position, "Resumen:")
    pdf.setFont("Helvetica", 10)
    pdf.setFillColor(text_color)
    pdf.drawString(margin_left, y_position - 15, f"Subtotal: ${valor_total_venta:,.2f}")
    pdf.drawString(margin_left, y_position - 30, f"IVA (19%): ${iva:,.2f}")
    pdf.drawString(margin_left, y_position - 45, f"Total: ${total:,.2f}")

    # Pie de página
    pdf.setFont("Helvetica", 8)
    pdf.setFillColor(text_color)
    pdf.drawString(margin_left, y_position - 80, "Gracias por su compra. Términos y condiciones disponibles en nuestro sitio web.")

    # Finalizar el PDF
    pdf.showPage()
    pdf.save()
    pdf_buffer.seek(0)

    return pdf_buffer

# Ruta para mostrar el historial de ventas
@app.route('/historial_ventas', methods=['GET'])
def historial_ventas():
    fecha_inicio = request.args.get('fecha_inicio')
    fecha_fin = request.args.get('fecha_fin')

    with sqlite3.connect('cadena_suministro.db') as conn:
        cursor = conn.cursor()
        
        if fecha_inicio and fecha_fin:
            cursor.execute('''
                SELECT id_venta, nombre_producto, cantidad_vendida, valor_total, fecha_venta
                FROM ventas
                WHERE fecha_venta BETWEEN ? AND ?
            ''', (fecha_inicio, fecha_fin))
        else:
            cursor.execute('''
                SELECT id_venta, nombre_producto, cantidad_vendida, valor_total, fecha_venta
                FROM ventas
            ''')

        ventas = cursor.fetchall()
        total_ventas = sum(venta[3] for venta in ventas)

    return render_template('historial_ventas.html', ventas=ventas, total_ventas=total_ventas)

# Ruta para eliminar una venta
@app.route('/eliminar_venta', methods=['POST'])
def eliminar_venta():
    venta_id = request.form['venta_id']
    nombre_producto = request.form['nombre_producto']
    cantidad_vendida = int(request.form['cantidad_vendida'])  # Convertir a entero
    conn = sqlite3.connect('cadena_suministro.db')
    cursor = conn.cursor()
    
    try:
        # Eliminar la venta de la tabla
        cursor.execute("DELETE FROM ventas WHERE id_venta = ?", (venta_id,))
        
        # Incrementar el inventario del producto
        cursor.execute("UPDATE inventario SET cantidad = cantidad + ? WHERE nombre_producto = ?", (cantidad_vendida, nombre_producto))
        
        conn.commit()
    except sqlite3.OperationalError as e:
        print(f"Error al eliminar la venta o actualizar el inventario: {e}")  # Imprimir el error para depuración
    finally:
        conn.close()
    
    return redirect(url_for('historial_ventas'))
# Ruta para productos más vendidos con filtro
@app.route('/productos_mas_vendidos')
def productos_mas_vendidos():
    # Obtener el filtro de periodo (día, semana, mes) del formulario
    periodo = request.args.get('periodo', 'dia')

    # Ajustar el intervalo de fecha según el periodo seleccionado
    query = """
    SELECT nombre_producto, SUM(cantidad_vendida) AS total_vendida
    FROM ventas
    WHERE fecha_venta >= DATE('now', ?)
    GROUP BY nombre_producto
    ORDER BY total_vendida DESC
    LIMIT 10
    """
    if periodo == 'semana':
        intervalo = '-7 days'
    elif periodo == 'mes':
        intervalo = '-30 days'
    else:
        intervalo = '0 days'

    # Obtener los datos de los productos más vendidos desde la base de datos
    with sqlite3.connect('cadena_suministro.db') as conn:
        cursor = conn.cursor()
        cursor.execute(query, (intervalo,))
        datos = cursor.fetchall()

    # Verificar que hay datos para graficar
    if not datos:
        return "No hay datos suficientes para mostrar los productos más vendidos."

    # Separar los datos en dos listas: nombres de productos y cantidades vendidas
    nombres_productos = [fila[0] for fila in datos]
    cantidades_vendidas = [fila[1] for fila in datos]

    # Crear la gráfica interactiva con Plotly
    fig = go.Figure(data=[go.Bar(x=nombres_productos, y=cantidades_vendidas, marker_color='skyblue')])
    fig.update_layout(
        title='Productos Más Vendidos',
        xaxis_title='Producto',
        yaxis_title='Cantidad Vendida',
        xaxis_tickangle=-45
    )

    # Convertir la gráfica a formato HTML para mostrar en la página web
    grafico_html = pio.to_html(fig, full_html=False)

    return render_template('productos_mas_vendidos.html', grafico_html=grafico_html)

###
# Cálculo del MRP y punto de reorden
def calcular_mrp(stock_actual, demanda, tiempo_entrega, umbral_seguridad):
    # Punto de reorden
    reorder_point = (demanda * tiempo_entrega) + umbral_seguridad
    return stock_actual < reorder_point
# Ruta para mostrar MRP y cuándo se debe reordenar
@app.route('/mrp')
def mostrar_mrp():
    conn = sqlite3.connect('cadena_suministro.db')
    cursor = conn.cursor()
    cursor.execute("SELECT nombre_producto, cantidad, demanda_estimada_diaria, tiempo_entrega, umbral_seguridad FROM inventario")
    inventario = cursor.fetchall()

    productos_a_reordenar = []
    nombres_productos = []
    cantidades_actuales = []
    cantidades_a_pedir = []

    for producto in inventario:
        nombre_producto, cantidad, demanda, tiempo_entrega, umbral_seguridad = producto
        
        if calcular_mrp(cantidad, demanda, tiempo_entrega, umbral_seguridad):
            cantidad_a_pedir = (demanda * tiempo_entrega + umbral_seguridad) - cantidad
            cantidad_a_pedir = max(cantidad_a_pedir, 0)
            fecha_pedido = datetime.now() + timedelta(days=tiempo_entrega)
            productos_a_reordenar.append({
                'nombre_producto': nombre_producto,
                'cantidad_actual': cantidad,
                'demanda': demanda,
                'tiempo_entrega': tiempo_entrega,
                'umbral_seguridad': umbral_seguridad,
                'cantidad_a_pedir': cantidad_a_pedir,
                'fecha_pedido': fecha_pedido.strftime('%Y-%m-%d')
            })
            
            # Agregar los datos para la gráfica
            nombres_productos.append(nombre_producto)
            cantidades_actuales.append(cantidad)
            cantidades_a_pedir.append(cantidad_a_pedir)

    conn.close()

    # Crear la gráfica
    fig, ax = plt.subplots()
    bar_width = 0.35  # Ancho de las barras
    x = np.arange(len(nombres_productos))  # Posiciones en el eje x

    # Gráfico de barras para la cantidad actual
    ax.bar(x - bar_width / 2, cantidades_actuales, width=bar_width, label='Cantidad Actual', alpha=0.6)

    # Gráfico de barras para la cantidad a pedir
    ax.bar(x + bar_width / 2, cantidades_a_pedir, width=bar_width, label='Cantidad a Pedir', alpha=0.6)

    # Configuraciones adicionales
    ax.set_ylabel('Cantidad')
    ax.set_title('Cantidad Actual vs Cantidad a Pedir')
    ax.set_xticks(x)
    ax.set_xticklabels(nombres_productos)
    ax.legend()

    # Guardar la gráfica en un objeto BytesIO
    img = BytesIO()
    plt.savefig(img, format='png')
    img.seek(0)
    grafica = base64.b64encode(img.getvalue()).decode()

    # Retornar los datos a la plantilla
    return render_template('mrp.html', productos_a_reordenar=productos_a_reordenar, 
                           grafica=grafica)






##PRONOSTICO


@app.route('/pronostico_ventas', methods=['GET'])
def pronostico_ventas():
    conn = sqlite3.connect('cadena_suministro.db')
    cursor = conn.cursor()

    # Obtener datos de ventas históricas
    query = """
        SELECT nombre_producto, SUM(cantidad_vendida) AS cantidad_vendida, strftime('%Y-%m', fecha_venta) AS mes
        FROM ventas
        GROUP BY nombre_producto, mes
        ORDER BY nombre_producto, mes
    """
    cursor.execute(query)
    datos = cursor.fetchall()
    conn.close()

    # Si no hay datos, pasar None para que el HTML muestre un mensaje adecuado
    if not datos:
        return render_template('pronostico_ventas.html', resultados=None)

    # Organizar datos en un DataFrame
    df = pd.DataFrame(datos, columns=['nombre_producto', 'cantidad_vendida', 'mes'])
    resultados = []

    for producto in df['nombre_producto'].unique():
        datos_producto = df[df['nombre_producto'] == producto].sort_values('mes')
        datos_producto.set_index('mes', inplace=True)
        datos_producto.index = pd.to_datetime(datos_producto.index)
        datos_producto = datos_producto.asfreq('MS').fillna(0)

        # Ajuste del modelo ARIMA
        try:
            modelo = ARIMA(datos_producto['cantidad_vendida'], order=(1, 1, 1))
            modelo_ajustado = modelo.fit()

            # Pronóstico para los próximos 12 meses
            pronostico = modelo_ajustado.forecast(steps=12)
            pronostico_index = pd.date_range(start=datos_producto.index[-1], periods=13, freq='M')[1:]

            # Crear gráfico con Plotly
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=datos_producto.index, y=datos_producto['cantidad_vendida'],
                                     mode='lines+markers', name='Histórico'))
            fig.add_trace(go.Scatter(x=pronostico_index, y=pronostico, mode='lines+markers',
                                     name='Pronóstico', line=dict(dash='dash')))

            fig.update_layout(title=f'Pronóstico de ventas para {producto}', xaxis_title='Fecha', yaxis_title='Cantidad Vendida')

            # Convertir figura a JSON para pasarlo a la plantilla
            grafico_json = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)

            # Agregar pronóstico a la lista de resultados
            resultados.append({
                'nombre_producto': producto,
                'pronostico_proximo_mes': int(round(pronostico[0])),
                'grafico': grafico_json
            })

        except Exception as e:
            print(f"Error en el modelo ARIMA para el producto {producto}: {e}")

    return render_template('pronostico_ventas.html', resultados=resultados)
























# Ruta para gráficos interactivos (indicadores)
@app.route('/indicadores')
def mostrar_indicadores():
    conn = sqlite3.connect('cadena_suministro.db')
    cursor = conn.cursor()
    cursor.execute("SELECT nombre_producto, cantidad FROM inventario")
    data = cursor.fetchall()

    nombres_productos = [item[0] for item in data]
    cantidades = [item[1] for item in data]
    
    conn.close()
    return render_template('indicadores.html', nombres=nombres_productos, cantidades=cantidades)

# Función para calcular la tasa de residuos
# Función para calcular la tasa de residuos
app.secret_key = 'tu_clave_secreta'
def calcular_tasa_residuos(residuos_anterior, residuos_actual):
    if residuos_anterior == 0:
        return None  # Evitar división por cero
    return (residuos_actual - residuos_anterior) / residuos_anterior * 100

def guardar_indicador(mes_anterior, residuos_anterior, mes_actual, residuos_actual, resultado):
    conn = sqlite3.connect('cadena_suministro.db')
    cursor = conn.cursor()
    cursor.execute(''' 
        INSERT INTO indicadores_residuos (mes_anterior, residuos_anterior, mes_actual, residuos_actual, resultado) 
        VALUES (?, ?, ?, ?, ?) 
    ''', (mes_anterior, residuos_anterior, mes_actual, residuos_actual, resultado))
    conn.commit()
    conn.close()

@app.route('/indicador_residuos', methods=['GET', 'POST'])
def indicador_residuos():
    if request.method == 'POST':
        try:
            mes_anterior = request.form['mes_anterior']
            residuos_anterior = float(request.form['residuos_anterior'])
            mes_actual = request.form['mes_actual']
            residuos_actual = float(request.form['residuos_actual'])

            if residuos_anterior < 0 or residuos_actual < 0:
                flash("Los valores de residuos no pueden ser negativos.")
                return redirect(url_for('indicador_residuos'))

            resultado = calcular_tasa_residuos(residuos_anterior, residuos_actual)
            if resultado is not None:
                guardar_indicador(mes_anterior, residuos_anterior, mes_actual, residuos_actual,resultado)
                return redirect(url_for('mostrar_resultados'))
            else:
                flash("El valor de residuos del periodo anterior no puede ser cero.")
                return redirect(url_for('indicador_residuos'))
        except ValueError:
            flash("Por favor, ingrese valores numéricos válidos.")
            return redirect(url_for('indicador_residuos'))

    return render_template('indicador_residuos.html')

@app.route('/resultados')
def mostrar_resultados():
    conn = sqlite3.connect('cadena_suministro.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM indicadores_residuos')
    resultados = cursor.fetchall()
    conn.close()

    resultados_coloreados = []
    for resultado in resultados:
        color = 'green'
        if resultado[4] > 20:
            color = 'red'
        elif 10 < resultado[4] <= 20:
            color = 'lightyellow'
        resultados_coloreados.append(resultado + (color,))

    # Extraer los datos de los meses y resultados (tasas de residuos en %)
    meses = [f"{resultado[1]} - {resultado[3]}" for resultado in resultados_coloreados]
    tasas_residuos = [resultado[4] for resultado in resultados_coloreados]  # Utilizar el resultado (%)

    # Crear la gráfica de dispersión con líneas
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=meses, y=tasas_residuos, mode='lines+markers', line=dict(color='blue')))
    fig.update_layout(
        title="Tasa de Residuos (%)",
        xaxis_title="Mes",
        yaxis_title="Tasa de Residuos (%)",
        template="plotly_white"  # Tema claro
    )

    # Guardar la gráfica como HTML
    graph_html = fig.to_html(full_html=False)

    return render_template('resultados.html', resultados=resultados_coloreados, graph_html=graph_html)

@app.route('/eliminar_indicador/<int:id>', methods=['POST'])
def eliminar_indicador(id):
    conn = sqlite3.connect('cadena_suministro.db')
    cursor = conn.cursor()
    cursor.execute('DELETE FROM indicadores_residuos WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    flash("El indicador ha sido eliminado correctamente.")
    return redirect(url_for('mostrar_resultados'))
### Función para calcular el indicador de logística ###
def calcular_indicador_logistica(cantidad_recibida, cantidad_solicitada):
    if cantidad_solicitada == 0:
        return None  # Evitar división por cero
    return (cantidad_recibida / cantidad_solicitada) * 100

# Función para guardar el indicador en la base de datos
def guardar_indicador_logistica(proveedor, cantidad_recibida, cantidad_solicitada, resultado2):  # Cambiado a guardar_indicador_logistica
    conn = sqlite3.connect('cadena_suministro.db')
    cursor = conn.cursor()
    cursor.execute(''' 
        INSERT INTO indicadores_logistica (proveedor, cantidad_recibida, cantidad_solicitada, resultado) 
        VALUES (?, ?, ?, ?) 
    ''', (proveedor, cantidad_recibida, cantidad_solicitada, resultado2))  # Cambiado a resultado2
    conn.commit()
    conn.close()

# Ruta para ingresar el indicador ##
@app.route('/indicador_logistica', methods=['GET', 'POST'])
def indicador_logistica():
    if request.method == 'POST':
        try:
            proveedor = request.form['proveedor']
            cantidad_recibida = float(request.form['cantidad_recibida'])
            cantidad_solicitada = float(request.form['cantidad_solicitada'])

            if cantidad_recibida < 0 or cantidad_solicitada < 0:
                flash("Las cantidades no pueden ser negativas.")
                return redirect(url_for('indicador_logistica'))

            resultado2 = calcular_indicador_logistica(cantidad_recibida, cantidad_solicitada)  # Cambiado a resultado2
            if resultado2 is not None:  # Cambiado a resultado2
                guardar_indicador_logistica(proveedor, cantidad_recibida, cantidad_solicitada, resultado2)  # Cambiado a guardar_indicador_logistica
                return redirect(url_for('mostrar_resultados_logistica'))  # Actualizado para reflejar la nueva ruta
            else:
                flash("La cantidad solicitada no puede ser cero.")
                return redirect(url_for('indicador_logistica'))
        except ValueError:
            flash("Por favor, ingrese valores numéricos válidos.")
            return redirect(url_for('indicador_logistica'))

    return render_template('indicador_logistica.html')

# Ruta para mostrar resultados
@app.route('/resultados_logistica')
def mostrar_resultados_logistica():
    conn = sqlite3.connect('cadena_suministro.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM indicadores_logistica')
    resultados = cursor.fetchall()
    conn.close()

    # Extraer los datos de los proveedores y sus resultados
    proveedores = [resultado[1] for resultado in resultados]  # Asumiendo que el proveedor está en la columna 1
    resultados_porcentaje = [resultado[4] for resultado in resultados]  # Asumiendo que el resultado está en la columna 4

    # Crear la gráfica de torta
    fig = go.Figure(data=[go.Pie(labels=proveedores, values=resultados_porcentaje)])
    fig.update_layout(title_text='Porcentaje de Indicadores por Proveedor')

    # Guardar la gráfica como HTML
    graph_html = fig.to_html(full_html=False)

    return render_template('resultados2.html', resultados=resultados, graph_html=graph_html)  # Se mantiene la referencia a resultados2.html

# Ruta para eliminar un indicador de logística
@app.route('/eliminar_indicador_logistica/<int:id>', methods=['POST'])
def eliminar_indicador_logistica(id):
    conn = sqlite3.connect('cadena_suministro.db')
    cursor = conn.cursor()
    cursor.execute('DELETE FROM indicadores_logistica WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    flash("El indicador ha sido eliminado correctamente.")
    return redirect(url_for('mostrar_resultados_logistica'))  # Cambiado para usar la nueva ruta

###indicador Reclamo
app.secret_key = 'tu_clave_secreta'
# Conexión a la base de datos
def get_db_connection():
    conn = sqlite3.connect('cadena_suministro.db')
    conn.row_factory = sqlite3.Row
    return conn

# Función para guardar el indicador de reclamos en la base de datos
def guardar_indicador_reclamos(mes, cantidad_reclamos, cantidad_clientes):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Calcular el porcentaje de reclamos
    porcentaje_reclamos = (cantidad_reclamos / cantidad_clientes) * 100 if cantidad_clientes > 0 else 0

    # Determinar el resultado y el color basado en el porcentaje
    if porcentaje_reclamos > 10:
        resultado = "Crítico"
        color = "Rojo"
    elif 5 <= porcentaje_reclamos <= 10:
        resultado = "Riesgo"
        color = "Amarillo"
    else:
        resultado = "Adecuado"
        color = "Verde"
    
    # Inserta todos los valores necesarios en la tabla
    cursor.execute('INSERT INTO indicador_reclamos (mes, cantidad_reclamos, cantidad_clientes, porcentaje_reclamos, resultado, color) VALUES (?, ?, ?, ?, ?, ?)',
                   (mes, cantidad_reclamos, cantidad_clientes, porcentaje_reclamos, resultado, color))
    
    conn.commit()
    conn.close()

# Ruta para calcular y guardar el indicador de reclamos
@app.route('/indicador_reclamos', methods=['GET', 'POST'])
def indicador_reclamos():
    if request.method == 'POST':
        try:
            mes = request.form['mes']
            cantidad_reclamos = int(request.form['cantidad_reclamos'])
            cantidad_clientes = int(request.form['cantidad_clientes'])

            if cantidad_reclamos < 0 or cantidad_clientes < 0:
                flash("Los valores de reclamos y clientes no pueden ser negativos.")
                return redirect(url_for('indicador_reclamos'))

            guardar_indicador_reclamos(mes, cantidad_reclamos, cantidad_clientes)
            return redirect(url_for('mostrar_resultados_reclamos'))
        except ValueError:
            flash("Por favor, ingrese valores numéricos válidos.")
            return redirect(url_for('indicador_reclamos'))

    return render_template('indicador_reclamos.html')

@app.route('/resultados_reclamos')
def mostrar_resultados_reclamos():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Selecciona todos los registros
    cursor.execute('SELECT * FROM indicador_reclamos ORDER BY mes')   
    resultados_reclamos = cursor.fetchall()
    conn.close()

    # Procesar resultados con colores según el porcentaje de reclamos
    resultados_coloreados = []
    meses = []
    porcentajes = []

    for resultado in resultados_reclamos:
        id_ = resultado['id']
        mes = resultado['mes']
        cantidad_reclamos = resultado['cantidad_reclamos']
        cantidad_clientes = resultado['cantidad_clientes']
        
        # Calcular porcentaje de reclamos
        if cantidad_clientes > 0:
            porcentaje_reclamos = (cantidad_reclamos / cantidad_clientes) * 100
        else:
            porcentaje_reclamos = 0  # Evitar división por cero

        # Clasificación de color según el porcentaje
        if porcentaje_reclamos < 5:
            color = 'green'
        elif 5 <= porcentaje_reclamos < 10:
            color = 'lightyellow'
        else:
            color = 'red'

        # Añadir el resultado procesado a la lista
        resultados_coloreados.append({
            'id': id_,
            'mes': mes,
            'cantidad_reclamos': cantidad_reclamos,
            'cantidad_clientes': cantidad_clientes,
            'porcentaje_reclamos': round(porcentaje_reclamos, 2),  # Redondear a 2 decimales
            'color': color
        })

        # Guardar datos para el gráfico
        meses.append(mes)  # Solo el mes, si no necesitas el año
        porcentajes.append(porcentaje_reclamos)

    # Crear la gráfica de dispersión con líneas
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=meses, y=porcentajes, mode='lines+markers', line=dict(color='blue')))
    fig.update_layout(
        title="Tasa de Reclamos (%)",
        xaxis_title="Mes",
        yaxis_title="Tasa de Reclamos (%)",
        template="plotly_white"  # Tema claro
    )

    # Guardar la gráfica como HTML
    graph_html = fig.to_html(full_html=False)

    return render_template('resultados_reclamos.html', resultados=resultados_coloreados, graph_html=graph_html)

# Ruta para eliminar un indicador de reclamos
@app.route('/eliminar_indicador_reclamos/<int:id>', methods=['POST'])
def eliminar_indicador_reclamos(id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM indicador_reclamos WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    flash("El indicador de reclamos ha sido eliminado correctamente.")
    return redirect(url_for('mostrar_resultados_reclamos'))

##indicador de rotacion
@app.route('/resultados_rotacion', methods=['GET'])
def resultados_rotacion():
    with sqlite3.connect('cadena_suministro.db') as conn:
        cursor = conn.cursor()
        cursor.execute('''
        SELECT 
            i.nombre_producto, 
            i.cantidad AS inventario_final,
            COALESCE(SUM(v.cantidad_vendida), 0) AS ventas_totales
        FROM 
            inventario i
        LEFT JOIN 
            ventas v ON i.nombre_producto = v.nombre_producto
        GROUP BY 
            i.nombre_producto, i.cantidad;
        ''')
        datos = cursor.fetchall()

    # Filtrar por fechas en Python
    resultados = []
    for producto, inventario_final, ventas_totales in datos:
        # Define las fechas del período (por ejemplo, octubre de 2024)
        ventas = 0
        with sqlite3.connect('cadena_suministro.db') as conn:
            cursor = conn.cursor()
            cursor.execute('''
            SELECT SUM(cantidad_vendida)
            FROM ventas
            WHERE nombre_producto = ?
              AND fecha_venta BETWEEN '2024-10-01' AND '2024-10-31';
            ''', (producto,))
            ventas = cursor.fetchone()[0] or 0

        inventario_inicial = inventario_final + ventas
        inventario_promedio = (inventario_inicial + inventario_final) / 2
        rotacion = ventas / inventario_promedio if inventario_promedio > 0 else 0
        resultados.append((producto, inventario_inicial, inventario_final, ventas, rotacion))

    return render_template('resultados_rotacion.html', resultados=resultados)


###########################################33

@app.route('/api/resultados_rotacion', methods=['GET'])
def api_resultados_rotacion():
    with sqlite3.connect('cadena_suministro.db') as conn:
        cursor = conn.cursor()
        cursor.execute('''
        SELECT i.nombre_producto, 
               SUM(i.cantidad) AS inventario_final,
               (SELECT SUM(cantidad_vendida) 
                FROM ventas 
                WHERE ventas.nombre_producto = i.nombre_producto) AS ventas
        FROM inventario i
        GROUP BY i.nombre_producto
        ''')
        datos = cursor.fetchall()

    resultados = []
    for producto, inventario_final, ventas in datos:
        inventario_inicial = inventario_final
        if inventario_inicial is None or ventas is None:
            continue
        inventario_promedio = inventario_inicial
        rotacion = ventas / inventario_promedio if inventario_promedio > 0 else 0
        resultados.append({
            "producto": producto,
            "inventario_inicial": inventario_inicial,
            "inventario_final": inventario_final,
            "ventas": ventas,
            "rotacion": rotacion
        })
    return jsonify(resultados)

# Función para obtener productos desde la base de datos (cadenas de suministro)
def obtener_productos():
    conn = sqlite3.connect('database.db')  # Cambia esto si usas otro tipo de base de datos
    cursor = conn.cursor()
    cursor.execute("SELECT nombre_producto FROM inventario")
    productos = cursor.fetchall()
    conn.close()
    return [producto[0] for producto in productos]

# Función para obtener datos de rotación por producto y mes
# Función para obtener productos desde la base de datos
def obtener_productos():
    conn = sqlite3.connect('cadena_suministro.db')  # Cambiado a cadena_suministro.db
    cursor = conn.cursor()
    cursor.execute("SELECT nombre_producto FROM inventario")
    productos = cursor.fetchall()
    conn.close()
    return [producto[0] for producto in productos]

# Función para obtener datos de rotación por producto y mes
# Conexión a la base de datos
def conectar_db():
    return sqlite3.connect('cadena_suministro.db')

# Función para obtener la rotación de inventarios de un producto para un mes específico
def obtener_rotacion(producto, mes):
    conn = conectar_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT mes, rotacion
        FROM rotacion
        WHERE producto = ? AND mes = ?
    """, (producto, mes))
    datos = cursor.fetchall()
    conn.close()

    # Devolver los datos como una lista de diccionarios
    return [{'mes': row[0], 'rotacion': row[1]} for row in datos]

# Ruta para obtener los resultados de rotación por producto y mes
@app.route('/api/rotacion_producto_mes/<producto>/<mes>')
def api_rotacion_producto_mes(producto, mes):
    resultados = obtener_rotacion(producto, mes)
    return jsonify(resultados)
if __name__ == '__main__':
    app.run(debug=True)
