import streamlit.components.v1 as components

# Configuración inicial de la página


import datetime
import pandas as pd
import psycopg2
import streamlit as st

# Configuración de la página
st.set_page_config(
    page_title="Control de Diésel", page_icon="⛽", layout="wide"
)


# --- FUNCIÓN DE AUTENTICACIÓN ---
def validar_usuario():
  """Muestra el formulario de login y bloquea la app hasta autenticar."""
  if "autenticado" not in st.session_state:
    st.session_state["autenticado"] = False

  if not st.session_state["autenticado"]:
    st.title("🔐 Acceso al Sistema")

    col1, col2 = st.columns([1, 2])
    with col1:
      usuario = st.text_input("Usuario")
      password = st.text_input("Contraseña", type="password")

      if st.button("Iniciar Sesión"):
        # Obtener credenciales desde secrets o valores por defecto
        user_ok = st.secrets.get("ADMIN_USER", "admin")
        pass_ok = st.secrets.get("ADMIN_PASSWORD", "1234")

        if usuario == user_ok and password == pass_ok:
          st.session_state["autenticado"] = True
          st.success("¡Acceso concedido!")
          st.rerun()
        else:
          st.error("Usuario o contraseña incorrectos.")

    return False
  return True


# --- CONTROL DE ACCESO ---
if not validar_usuario():
  st.stop()  # Detiene la ejecución para no mostrar el resto de la app

# --- BOTÓN PARA CERRAR SESIÓN EN LA BARRA LATERAL ---
with st.sidebar:
  st.write(f"👤 **Usuario:** {st.secrets.get('ADMIN_USER', 'admin')}")
  if st.button("🚪 Cerrar Sesión"):
    st.session_state["autenticado"] = False
    st.rerun()

# --- A PARTIR DE AQUÍ CONTINÚA TU CÓDIGO NORMAL ---


# Pestañas y contenido de la app...
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


# ==========================================
# BACKEND COMPATIBLE CON POSTGRESQL (SUPABASE)
# ==========================================
def generar_ticket_html(
    id_venta, fecha, cliente, galones, precio_galon, total, *args
):
  # Conversiones seguras
  try:
    id_num = f"{int(id_venta):06d}"
  except (ValueError, TypeError):
    id_num = str(id_venta)

  try:
    galones_num = f"{float(galones):.2f}"
  except (ValueError, TypeError):
    galones_num = str(galones)

  try:
    precio_num = f"{float(precio_galon):.2f}"
  except (ValueError, TypeError):
    precio_num = str(precio_galon)

  try:
    total_num = f"{float(total):.2f}"
  except (ValueError, TypeError):
    total_num = str(total)

  cliente_nombre = str(cliente) if cliente else "Cliente Varios"

  html_code = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            @page {{
                size: 80mm auto;
                margin: 0mm;
            }}
            body {{
                width: 78mm;
                font-family: 'Courier New', Courier, monospace;
                font-size: 13px;
                line-height: 1.2;
                color: #000;
                background-color: #fff;
                margin: 0 auto;
                padding: 10px 5px;
            }}
            .text-center {{ text-align: center; }}
            .text-right {{ text-align: right; }}
            .bold {{ font-weight: bold; }}
            .linea {{ border-top: 1px dashed #000; margin: 8px 0; }}
            table {{ width: 100%; border-collapse: collapse; font-size: 12px; }}
            th, td {{ text-align: left; padding: 2px 0; }}
            .btn-print {{
                display: block;
                width: 100%;
                background-color: #007bff;
                color: white;
                padding: 10px;
                text-align: center;
                font-size: 16px;
                border: none;
                border-radius: 5px;
                cursor: pointer;
                margin-bottom: 15px;
            }}
            @media print {{
                .btn-print {{ display: none; }}
            }}
        </style>
    </head>
    <body>
        <button class="btn-print" onclick="window.print()">🖨️ IMPRIMIR TICKET</button>
        
        <div class="text-center bold" style="font-size: 16px;">ESTACIÓN DE SERVICIO WM</div>
        <div class="text-center">Venta de Combustible / Diésel</div>
        
        <div class="linea"></div>
        
        <div><b>Ticket:</b> #{id_num}</div>
        <div><b>Fecha:</b> {fecha}</div>
        <div><b>Cliente:</b> {cliente_nombre}</div>
        
        <div class="linea"></div>
        
        <table>
            <thead>
                <tr>
                    <th>DESCRIPCIÓN</th>
                    <th class="text-right">CANT.</th>
                    <th class="text-right">TOTAL</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td>DIÉSEL B5</td>
                    <td class="text-right">{galones_num} G.</td>
                    <td class="text-right">S/ {total_num}</td>
                </tr>
            </tbody>
        </table>
        
        <div class="linea"></div>
        
        <div class="text-right"><b>Precio/Galón:</b> S/ {precio_num}</div>
        <div class="text-right bold" style="font-size: 16px; margin-top: 5px;">
            TOTAL A PAGAR: S/ {total_num}
        </div>
        
        <div class="linea"></div>
        <div class="text-center" style="margin-top: 10px;">¡Gracias por su compra!</div>
    </body>
    </html>
    """
  return html_code

def obtener_conexion():
  url_conexion = None

  # Intenta leer desde Secrets si estás en Streamlit Cloud
  try:
    if hasattr(st, "secrets") and "DATABASE_URL" in st.secrets:
      url_conexion = st.secrets["DATABASE_URL"]
  except Exception:
    url_conexion = None

  # Si estás en tu PC local:
  if not url_conexion:
    # URL CON EL POOLER (Puerto 6543 y aws-0-...)
    url_conexion = "postgresql://postgres.tqgrocjrhmtjtkdjfivm:salva97leo.@aws-0-sa-east-1.pooler.supabase.com:6543/postgres?sslmode=require"

  return psycopg2.connect(url_conexion)


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
def anular_venta(id_venta):
  """Devuelve los galones al inventario y elimina el registro de la venta."""
  try:
    conn = obtener_conexion()
    cursor = conn.cursor()

    # 1. Obtener los galones de la venta a anular
    cursor.execute("SELECT galones FROM ventas WHERE id = %s;", (id_venta,))
    res = cursor.fetchone()

    if res:
      galones_a_devolver = res[0]

      # 2. Sumar los galones de vuelta al inventario
      cursor.execute(
          """
                UPDATE inventario 
                SET stock_galones = stock_galones + %s 
                WHERE id = (SELECT id FROM inventario ORDER BY id ASC LIMIT 1);
            """,
          (galones_a_devolver,),
      )

      # 3. Eliminar la venta del historial
      cursor.execute("DELETE FROM ventas WHERE id = %s;", (id_venta,))

      conn.commit()
      st.success(
          f"✅ Venta #{id_venta} anulada correctamente. Se devolvieron"
          f" {galones_a_devolver:.2f} galones al stock."
      )
    else:
      st.error("No se encontró ninguna venta con ese ID.")

    cursor.close()
    conn.close()
  except Exception as e:
    st.error(f"Error al anular la venta: {e}")
# --- FUNCIÓN PARA OBTENER LAS ÚLTIMAS VENTAS ---
def obtener_ultimas_ventas():
  try:
    conn = obtener_conexion()
    cursor = conn.cursor()
    # Trae los datos de las últimas 20 ventas
    cursor.execute(
        "SELECT id, fecha, galones, total FROM ventas ORDER BY id DESC LIMIT"
        " 20;"
    )
    ventas = cursor.fetchall()
    cursor.close()
    conn.close()
    return ventas
  except Exception as e:
    st.error(f"Error al obtener ventas: {e}")
    return []


# --- INTERFAZ PARA ANULAR VENTA ---
with st.expander("🚨 Anular / Borrar una Venta Errónea"):
  ventas_disponibles = obtener_ultimas_ventas()

  if ventas_disponibles:
    # Creamos un diccionario para mostrar texto claro y guardar el ID interno
    opciones_ventas = {
        f"ID #{v[0]} | Fecha: {v[1]} | {v[2]} galones | Total: S/{v[3]}": v[0]
        for v in ventas_disponibles
    }

    venta_seleccionada = st.selectbox(
        "Seleccione la venta que desea eliminar:", list(opciones_ventas.keys())
    )

    # Extraemos el ID exacto asignado a la opción elegida
    id_a_borrar = opciones_ventas[venta_seleccionada]

    if st.button("Confirmar Anulación",key="btn_anular_venta"):
      anular_venta(int(id_a_borrar))  # Aseguramos que sea entero
      st.rerun()
  else:
    st.info("No hay ventas registradas para anular.")

# ==========================================
# 2. FRONTEND: Interfaz de Usuario
# ==========================================


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
                st.rerun()  # Cambiar a st.rerun() si actualizaste Streamlit

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
        
        st.dataframe(df)
    else:
        st.info("No hay ventas registradas aún.")
# Sección dentro de la pestaña de Historial/Reportes

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

        
