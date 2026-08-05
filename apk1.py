
import streamlit.components.v1 as components

# Configuración inicial de la página


import datetime
import pandas as pd
import psycopg2
import streamlit as st

# ==========================================
# BACKEND COMPATIBLE CON POSTGRESQL (SUPABASE)
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
  """Establece conexión con PostgreSQL en Supabase detectando si está en local o en la nube."""
  url_conexion = None

  # 1. Intentamos leer los Secretos (funciona automáticamente cuando está subido a Streamlit Cloud)
  try:
    if "DATABASE_URL" in st.secrets:
      url_conexion = st.secrets["DATABASE_URL"]
  except Exception:
    pass

  # 2. Si estamos ejecutando en la computadora (local), usamos la URL directamente
  if not url_conexion:
    # REEMPLAZA CON TU URL REAL DE SUPABASE
    url_conexion = "postgresql://postgres:TU_CONTRASEÑA@aws-0-sa-east-1.pooler.supabase.com:6543/postgres"

  return psycopg2.connect(url_conexion)

def inicializar_bd():
  """Crea las tablas en PostgreSQL si no existen e inicializa el stock."""
  conn = obtener_conexion()
  cursor = conn.cursor()
  try:
    cursor.execute("""
            CREATE TABLE IF NOT EXISTS inventario (
                id SERIAL PRIMARY KEY,
                stock_galones REAL
            )
        """)

    cursor.execute("""
            CREATE TABLE IF NOT EXISTS ventas (
                id SERIAL PRIMARY KEY,
                cliente TEXT,
                galones REAL,
                precio_galon REAL,
                total REAL,
                fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

    cursor.execute("""
            CREATE TABLE IF NOT EXISTS ingresos (
                id SERIAL PRIMARY KEY,
                proveedor TEXT,
                galones REAL,
                costo_total REAL,
                fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

    cursor.execute("SELECT COUNT(*) FROM inventario")
    if cursor.fetchone()[0] == 0:
      cursor.execute("INSERT INTO inventario (stock_galones) VALUES (%s)", (1000.0,))

    conn.commit()
  finally:
    cursor.close()
    conn.close()


def obtener_stock():
  """Obtiene el stock actual de diésel."""
  conn = obtener_conexion()
  cursor = conn.cursor()
  try:
    cursor.execute(
        "SELECT stock_galones FROM inventario ORDER BY id ASC LIMIT 1"
    )
    res = cursor.fetchone()
    return res[0] if res else 0.0
  finally:
    cursor.close()
    conn.close()


def registrar_venta(cliente, galones, precio_galon):
  """Registra una venta y descuenta stock en PostgreSQL."""
  conn = obtener_conexion()
  cursor = conn.cursor()
  try:
    cursor.execute(
        "SELECT stock_galones FROM inventario ORDER BY id ASC LIMIT 1"
    )
    stock_actual = cursor.fetchone()[0]

    if galones > stock_actual:
      return (
          False,
          f"Stock insuficiente. Solo quedan {stock_actual:.2f} galones.",
      )

    total = galones * precio_galon
    nuevo_stock = stock_actual - galones

    # Actualizar stock
    cursor.execute(
        "UPDATE inventario SET stock_galones = %s WHERE id = (SELECT id FROM"
        " inventario ORDER BY id ASC LIMIT 1)",
        (nuevo_stock,),
    )

    # Insertar registro de venta
    cursor.execute(
        """
            INSERT INTO ventas (cliente, galones, precio_galon, total)
            VALUES (%s, %s, %s, %s)
        """,
        (cliente, galones, precio_galon, total),
    )

    conn.commit()
    return True, f"Venta registrada con éxito. Total: S/ {total:.2f}"
  except Exception as e:
    conn.rollback()
    return False, f"Error al registrar la venta: {e}"
  finally:
    cursor.close()
    conn.close()


def registrar_ingreso(proveedor, galones, costo_total):
  """Registra la llegada de cisterna y aumenta el stock."""
  conn = obtener_conexion()
  cursor = conn.cursor()
  try:
    cursor.execute(
        "SELECT stock_galones FROM inventario ORDER BY id ASC LIMIT 1"
    )
    stock_actual = cursor.fetchone()[0]
    nuevo_stock = stock_actual + galones

    # Actualizar stock
    cursor.execute(
        "UPDATE inventario SET stock_galones = %s WHERE id = (SELECT id FROM"
        " inventario ORDER BY id ASC LIMIT 1)",
        (nuevo_stock,),
    )

    # Insertar registro de ingreso
    cursor.execute(
        """
            INSERT INTO ingresos (proveedor, galones, costo_total)
            VALUES (%s, %s, %s)
        """,
        (proveedor, galones, costo_total),
    )

    conn.commit()
    return True, f"Ingreso registrado. Nuevo stock: {nuevo_stock:.2f} galones."
  except Exception as e:
    conn.rollback()
    return False, f"Error al registrar el ingreso: {e}"
  finally:
    cursor.close()
    conn.close()


def obtener_historial_ventas():
  """Obtiene las últimas 10 ventas registradas."""
  conn = obtener_conexion()
  cursor = conn.cursor()
  try:
    cursor.execute("""
            SELECT fecha, cliente, galones, precio_galon, total 
            FROM ventas 
            ORDER BY fecha DESC 
            LIMIT 10
        """)
    filas = cursor.fetchall()
    return filas
  finally:
    cursor.close()
    conn.close()


def obtener_reporte_ventas(fecha_inicio, fecha_fin):
  """Filtra las ventas en PostgreSQL dentro de un rango de fechas."""
  conn = obtener_conexion()
  cursor = conn.cursor()
  try:
    cursor.execute(
        """
            SELECT fecha, cliente, galones, precio_galon, total 
            FROM ventas 
            WHERE fecha::date BETWEEN %s AND %s
            ORDER BY fecha DESC
        """,
        (fecha_inicio, fecha_fin),
    )
    filas = cursor.fetchall()
    return filas
  finally:
    cursor.close()
    conn.close()


# ==========================================
# 2. FRONTEND: Interfaz de Usuario
# ==========================================
def inicializar_bd():
  """Crea las tablas en PostgreSQL (Supabase) si no existen e inicializa el stock."""
  conn = obtener_conexion()
  cursor = conn.cursor()
  try:
    # Tabla de Inventario
    cursor.execute("""
            CREATE TABLE IF NOT EXISTS inventario (
                id SERIAL PRIMARY KEY,
                stock_galones REAL NOT NULL
            );
        """)

    # Tabla de Ventas
    cursor.execute("""
            CREATE TABLE IF NOT EXISTS ventas (
                id SERIAL PRIMARY KEY,
                cliente TEXT NOT NULL,
                galones REAL NOT NULL,
                precio_galon REAL NOT NULL,
                total REAL NOT NULL,
                fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

    # Tabla de Ingresos (Cisterna)
    cursor.execute("""
            CREATE TABLE IF NOT EXISTS ingresos (
                id SERIAL PRIMARY KEY,
                proveedor TEXT NOT NULL,
                galones REAL NOT NULL,
                costo_total REAL NOT NULL,
                fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

    # Verificar si el inventario tiene un registro base
    cursor.execute("SELECT COUNT(*) FROM inventario;")
    count = cursor.fetchone()[0]

    if count == 0:
      cursor.execute(
          "INSERT INTO inventario (stock_galones) VALUES (%s);", (1000.0,)
      )

    # Confirmar todos los cambios en la base de datos
    conn.commit()

  except Exception as e:
    # Si hay algún error, deshacer cambios pendientes
    conn.rollback()
    st.error(f"Error al inicializar la base de datos: {e}")
  finally:
    cursor.close()
    conn.close()
    
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
        precio_galon = st.number_input("Precio por Galón", min_value=0.1, value=15.50, step=0.10)
        
        btn_vender = st.form_submit_button("Confirmar Venta")
        
    if btn_vender:
        if not cliente:
            st.warning("Escribe el nombre del cliente.")
        else:
            exito, msj = registrar_venta(cliente, galones, precio_galon)
            # Dentro de: if btn_vender:
        if exito:
            st.success(msj)
            
            # Obtener la última venta registrada en Supabase
            conn = obtener_conexion()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, TO_CHAR(fecha, 'YYYY-MM-DD HH24:MI') 
                FROM ventas 
                ORDER BY id DESC LIMIT 1
            """)
            res = cursor.fetchone()
            cursor.close()
            conn.close()
            
            if res:
                id_venta, fecha_str = res[0], res[1]
                total_venta = galones * precio_galon
                
                # Generar ticket
                ticket_html = generar_ticket_html(
                    id_venta, 
                    fecha_str, 
                    cliente, 
                    galones, 
                    precio_galon, 
                    total_venta
                )
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
# PESTAÑA 3: ÚLTIMOS MOVIMIENTOS (Ajustado para Supabase)
with tab_historial:
    st.subheader("Historial de Ventas")
    ventas = obtener_historial_ventas()
    
    if ventas:
        df = pd.DataFrame(
            ventas, 
            columns=["Fecha y Hora", "Cliente", "Galones", "Precio/Gal (S/)", "Total (S/)"]
        )
        
        # Formatear la fecha para limpiar los microsegundos de PostgreSQL
        df["Fecha y Hora"] = pd.to_datetime(df["Fecha y Hora"]).dt.strftime('%Y-%m-%d %H:%M')
        
        st.dataframe(df, use_container_width=True)
    else:
        st.info("No hay ventas registradas aún.")

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

        
