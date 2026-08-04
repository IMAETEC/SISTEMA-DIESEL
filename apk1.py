import sqlite3
import streamlit as st
import streamlit.components.v1 as components

# Configuración inicial de la página
st.set_page_config(page_title="Sistema Diésel", page_icon="⛽", layout="centered")

# ==========================================
# 1. BACKEND: Conexión y Base de Datos
# ==========================================


def generar_ticket_html(id_venta, fecha, cliente, galones, precio_galon, total):
    """Genera la estructura del ticket en HTML y el script para imprimir."""
    html_ticket = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{
                font-family: 'Courier New', Courier, monospace;
                width: 280px;
                margin: 0 auto;
                padding: 10px;
                background-color: #fff;
                color: #000;
            }}
            .text-center {{ text-align: center; }}
            .linea {{ border-top: 1px dashed #000; margin: 8px 0; }}
            .flex-between {{ display: flex; justify-content: space-between; }}
            .bold {{ font-weight: bold; }}
            @media print {{
                .no-print {{ display: none; }}
            }}
        </style>
    </head>
    <body>
        <div class="text-center">
            <h3 style="margin:0;">ESTACIÓN DE SERVICIO</h3>
            <p style="margin:2px 0;">Control de Diésel</p>
            <p style="margin:2px 0; font-size: 12px;">Ticket N°: #{id_venta:05d}</p>
            <p style="margin:2px 0; font-size: 12px;">Fecha: {fecha}</p>
        </div>
        
        <div class="linea"></div>
        
        <p style="margin:4px 0; font-size: 13px;"><strong>Cliente:</strong> {cliente}</p>
        
        <div class="linea"></div>
        
        <div class="flex-between" style="font-size: 13px;">
            <span>Producto:</span>
            <span>Diésel B5</span>
        </div>
        <div class="flex-between" style="font-size: 13px;">
            <span>Cantidad:</span>
            <span>{galones:.2f} Gal</span>
        </div>
        <div class="flex-between" style="font-size: 13px;">
            <span>Precio / Gal:</span>
            <span>S/ {precio_galon:.2f}</span>
        </div>
        
        <div class="linea"></div>
        
        <div class="flex-between bold" style="font-size: 15px;">
            <span>TOTAL:</span>
            <span>S/ {total:.2f}</span>
        </div>
        
        <div class="linea"></div>
        
        <p class="text-center" style="font-size: 11px; margin-top: 10px;">¡Gracias por su compra!</p>
        
        <!-- Botón que activa la impresión del sistema operativo -->
        <div class="text-center no-print" style="margin-top: 15px;">
            <button onclick="window.print()" style="padding: 8px 16px; background-color: #007bff; color: white; border: none; border-radius: 4px; cursor: pointer;">
                🖨️ Imprimir Ticket
            </button>
        </div>
    </body>
    </html>
    """
    return html_ticket

def obtener_conexion():
    conn = sqlite3.connect("diesel.db")
    return conn

def inicializar_bd():
    """Crea las tablas necesarias si no existen."""
    conn = obtener_conexion()
    cursor = conn.cursor()
    
    # Tabla de Inventario
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS inventario (
            id INTEGER PRIMARY KEY,
            stock_galones REAL
        )
    """)
    
    # Tabla de Ventas
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ventas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cliente TEXT,
            galones REAL,
            precio_galon REAL,
            total REAL,
            fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Tabla de Ingresos / Compras
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ingresos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            proveedor TEXT,
            galones REAL,
            costo_total REAL,
            fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Si no hay inventario registrado, iniciamos con 1000 galones
    cursor.execute("SELECT COUNT(*) FROM inventario")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO inventario (id, stock_galones) VALUES (1, 1000.0)")
        
    conn.commit()
    conn.close()

def obtener_stock():
    conn = obtener_conexion()
    cursor = conn.cursor()
    cursor.execute("SELECT stock_galones FROM inventario WHERE id = 1")
    stock = cursor.fetchone()[0]
    conn.close()
    return stock

def registrar_venta(cliente, galones, precio_galon):
    """Procesa una venta y resta galones del stock."""
    conn = obtener_conexion()
    cursor = conn.cursor()
    
    cursor.execute("SELECT stock_galones FROM inventario WHERE id = 1")
    stock_actual = cursor.fetchone()[0]
    
    if galones > stock_actual:
        conn.close()
        return False, f"Stock insuficiente. Solo quedan {stock_actual:.2f} galones."
    
    total = galones * precio_galon
    nuevo_stock = stock_actual - galones
    
    cursor.execute("UPDATE inventario SET stock_galones = ? WHERE id = 1", (nuevo_stock,))
    cursor.execute("""
        INSERT INTO ventas (cliente, galones, precio_galon, total)
        VALUES (?, ?, ?, ?)
    """, (cliente, galones, precio_galon, total))
    
    conn.commit()
    conn.close()
    return True, f"Venta registrada con éxito. Total: S/ {total:.2f}"

def registrar_ingreso(proveedor, galones, costo_total):
    """Procesa la recarga de diésel y suma galones al stock."""
    conn = obtener_conexion()
    cursor = conn.cursor()
    
    cursor.execute("SELECT stock_galones FROM inventario WHERE id = 1")
    stock_actual = cursor.fetchone()[0]
    nuevo_stock = stock_actual + galones
    
    cursor.execute("UPDATE inventario SET stock_galones = ? WHERE id = 1", (nuevo_stock,))
    cursor.execute("""
        INSERT INTO ingresos (proveedor, galones, costo_total)
        VALUES (?, ?, ?)
    """, (proveedor, galones, costo_total))
    
    conn.commit()
    conn.close()
    return True, f"Ingreso registrado. Nuevo stock: {nuevo_stock:.2f} galones."

def obtener_historial_ventas():
    conn = obtener_conexion()
    cursor = conn.cursor()
    cursor.execute("SELECT fecha, cliente, galones, precio_galon, total FROM ventas ORDER BY fecha DESC LIMIT 10")
    filas = cursor.fetchall()
    conn.close()
    return filas
def obtener_reporte_ventas(fecha_inicio, fecha_fin):
    """Filtra las ventas entre un rango de fechas dado."""
    conn = obtener_conexion()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT fecha, cliente, galones, precio_galon, total 
        FROM ventas 
        WHERE DATE(fecha) BETWEEN ? AND ?
        ORDER BY fecha DESC
    """, (fecha_inicio, fecha_fin))
    filas = cursor.fetchall()
    conn.close()
    return filas        


# ==========================================
# 2. FRONTEND: Interfaz de Usuario
# ==========================================
inicializar_bd()

st.title("⛽ Control de Diésel")

# Indicador principal de Stock
stock_actual = obtener_stock()
st.metric(label="Stock Actual de Diésel", value=f"{stock_actual:.2f} Galones")

st.markdown("---")

# Creación de pestañas para organizar las opciones
tab_venta, tab_ingreso, tab_historial, tab_reporte = st.tabs([
    "🛒 Nueva Venta", 
    "🚛 Ingreso Cisterna", 
    "📊 Últimos Movimientos", 
    "📄 Reportes"
])
# ------------------------------------------
# PESTAÑA 1: REGISTRAR VENTA
# ------------------------------------------
# Modificación en la PESTAÑA 1 (tab_venta)
with tab_venta:
    st.subheader("Registrar Venta de Diésel")
    with st.form("form_venta", clear_on_submit=False):
        cliente = st.text_input("Nombre del Cliente", placeholder="Ej. Juan Pérez")
        galones = st.number_input("Cantidad de Galones a vender", min_value=0.1, step=1.0)
        precio_galon = st.number_input("Precio por Galón", min_value=0.1, value=20.3, step=0.10)
        
        btn_vender = st.form_submit_button("Confirmar Venta")
        
    if btn_vender:
        if not cliente:
            st.warning("Escribe el nombre del cliente.")
        else:
            exito, msj = registrar_venta(cliente, galones, precio_galon)
            if exito:
                st.success(msj)
                
                # Obtener el ID de la última venta para generar el ticket
                conn = obtener_conexion()
                cursor = conn.cursor()
                cursor.execute("SELECT id, fecha FROM ventas ORDER BY id DESC LIMIT 1")
                id_venta, fecha_venta = cursor.fetchone()
                conn.close()
                
                # Renderizar el comprobante en la pantalla
                st.markdown("### 📄 Comprobante Generado")
                total_venta = galones * precio_galon
                ticket_html = generar_ticket_html(id_venta, fecha_venta, cliente, galones, precio_galon, total_venta)
                
                # Mostramos el HTML embebido en la aplicación
                components.html(ticket_html, height=350, scrolling=True)
            else:
                st.error(msj)

# ------------------------------------------
# PESTAÑA 2: REGISTRAR INGRESO (CISTERNA)
# ------------------------------------------
with tab_ingreso:
    st.subheader("Registrar Recarga de Tanque")
    with st.form("form_ingreso", clear_on_submit=True):
        proveedor = st.text_input("Proveedor / N° Guía", placeholder="Ej. Primax / Guía #4521")
        galones_ingreso = st.number_input("Galones Ingresados", min_value=1.0, step=50.0)
        costo_total = st.number_input("Costo Total de Recarga", min_value=0.0, step=100.0)
        
        btn_ingresar = st.form_submit_button("Cargar al Inventario")
        
    if btn_ingresar:
        if not proveedor:
            st.warning("Escribe el proveedor o número de guía.")
        else:
            exito, msj = registrar_ingreso(proveedor, galones_ingreso, costo_total)
            if exito:
                st.success(msj)
                st.experimental_rerun()  # Cambiar a st.rerun() si actualizaste Streamlit

# ------------------------------------------
# PESTAÑA 3: HISTORIAL DE MOVIMIENTOS
# ------------------------------------------
with tab_historial:
    st.subheader("Últimas 10 Ventas")
    ventas = obtener_historial_ventas()
    
    if ventas:
        # Mostramos una tabla sencilla con los datos
        import pandas as pd
        df_ventas = pd.DataFrame(
            ventas,
            columns=["fecha y hora","cliente","galones","precio/gal (S/)","total (S/)"]
        )
        st.dataframe(df_ventas)
    else:
        st.info("Aún no hay ventas registradas.")
import datetime

# Actualizamos las pestañas a 4 opciones


# ... (Mantienes el contenido de las pestañas 1, 2 y 3) ...

# ------------------------------------------
# PESTAÑA 4: REPORTES Y COMPROBANTES
# ------------------------------------------
with tab_reporte:
    st.subheader("Generar Reporte de Ventas")
    
    col1, col2 = st.columns(2)
    with col1:
        fecha_inicio = st.date_input("Fecha Inicio", datetime.date.today())
    with col2:
        fecha_fin = st.date_input("Fecha Fin", datetime.date.today())
        
    if st.button("Buscar Ventas"):
        ventas_reporte = obtener_reporte_ventas(fecha_inicio, fecha_fin)
        
        if ventas_reporte:
            df_rep = pd.DataFrame(
                ventas_reporte, 
                columns=["Fecha y Hora", "Cliente", "Galones", "Precio/Gal (S/)", "Total (S/)"]
            )
            
            # Totales acumulados en el periodo
            total_galones = df_rep["Galones"].sum()
            total_dinero = df_rep["Total (S/)"].sum()
            
            st.success(f"**Resumen:** {total_galones:.2f} Galones vendidos | **Total Recaudado:** S/ {total_dinero:.2f}")
            st.dataframe(df_rep)
        else:
            st.warning("No se encontraron ventas en ese rango de fechas.")

        
