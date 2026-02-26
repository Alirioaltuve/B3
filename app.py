import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

# ==========================================
# 1. CONFIGURACIÓN DE LA PÁGINA
# ==========================================
st.set_page_config(
    page_title="Punto de Venta VZLA", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==========================================
# 2. FUNCIONES DE BASE DE DATOS (SQLITE)
# ==========================================

def conectar():
    """Establece conexión con el archivo de base de datos local."""
    return sqlite3.connect('inventario.db')

def crear_db():
    """Crea las tablas necesarias si no existen al iniciar la app."""
    conn = conectar()
    c = conn.cursor()
    # Tabla para guardar los productos del negocio
    c.execute('''CREATE TABLE IF NOT EXISTS productos 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  nombre TEXT, 
                  categoria TEXT, 
                  precio_usd REAL)''')
    
    # Tabla para guardar el historial de cada venta realizada
    c.execute('''CREATE TABLE IF NOT EXISTS ventas 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  fecha TEXT, 
                  productos TEXT, 
                  total_usd REAL, 
                  tasa_bs REAL, 
                  total_bs REAL)''')
    conn.commit()
    conn.close()

def obtener_productos():
    """Recupera todos los productos de la DB y los devuelve como un DataFrame de Pandas."""
    conn = conectar()
    df = pd.read_sql_query("SELECT * FROM productos ORDER BY nombre ASC", conn)
    conn.close()
    return df

def registrar_venta(lista_productos, total_u, tasa, total_b):
    """Guarda una nueva fila en la tabla de ventas con el detalle de la compra."""
    conn = conectar()
    c = conn.cursor()
    # Unimos los nombres de los productos en un solo texto separado por comas
    nombres_prod = ", ".join([p['nombre'] for p in lista_productos])
    # Obtenemos la fecha y hora actual de la computadora
    fecha_hoy = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    
    c.execute("INSERT INTO ventas (fecha, productos, total_usd, tasa_bs, total_bs) VALUES (?, ?, ?, ?, ?)",
              (fecha_hoy, nombres_prod, total_u, tasa, total_b))
    conn.commit()
    conn.close()

# ==========================================
# 3. INICIALIZACIÓN Y SIDEBAR
# ==========================================

# Ejecutamos la creación de tablas al cargar
crear_db()

# 'session_state' sirve para que los datos del carrito no se borren al hacer click en botones
if 'carrito' not in st.session_state:
    st.session_state.carrito = []

# Sidebar: Configuración de la tasa del dólar
st.sidebar.title("💰 Control de Tasa")
tasa_dolar = st.sidebar.number_input(
    "Tasa del Día (Bs.)", 
    min_value=1.0, 
    value=36.5, 
    step=0.1,
    help="Actualiza este valor según el BCV o paralelo para calcular precios al instante."
)

st.sidebar.markdown("---")
st.sidebar.info("Usa este panel para ajustar el cambio antes de empezar a vender.")

# ==========================================
# 4. INTERFAZ PRINCIPAL (TABS)
# ==========================================

tab1, tab2, tab3 = st.tabs(["🛒 Punto de Venta", "⚙️ Inventario", "📄 Historial"])

# --- TAB 1: SISTEMA DE VENTAS ---
with tab1:
    col_productos, col_carrito = st.columns([2, 1])
    
    with col_productos:
        st.subheader("🔍 Buscador de Productos")
        busqueda = st.text_input("Escribe el nombre del producto...", placeholder="Ej: Harina")
        
        df_p = obtener_productos()
        if not df_p.empty:
            # Filtramos el DataFrame según lo que el usuario escribe
            filtro = df_p[df_p['nombre'].str.contains(busqueda, case=False)]
            
            for _, row in filtro.iterrows():
                # Calculamos el precio en bolívares al vuelo (sin guardarlo en DB)
                p_bs = row['precio_usd'] * tasa_dolar
                
                # Botón de producto: al pulsar se agrega a la lista del carrito
                if st.button(f"{row['nombre']} | ${row['precio_usd']:.2f} ({p_bs:,.2f} Bs)", key=f"v_btn_{row['id']}", use_container_width=True):
                    st.session_state.carrito.append(row)
                    st.toast(f"Agregado: {row['nombre']}")
        else:
            st.warning("No hay productos cargados. Ve a la pestaña de Inventario.")

    with col_carrito:
        st.subheader("📝 Cuenta")
        if st.session_state.carrito:
            # Cálculos totales
            t_usd = sum(item['precio_usd'] for item in st.session_state.carrito)
            t_bs = t_usd * tasa_dolar
            
            # Listado visual de lo que se va agregando
            for item in st.session_state.carrito:
                st.write(f"• {item['nombre']} (${item['precio_usd']:.2f})")
            
            st.divider()
            st.metric("TOTAL BS.", f"{t_bs:,.2f}")
            st.write(f"Total Divisa: ${t_usd:,.2f}")
            
            # Acción para guardar la venta
            if st.button("✅ FINALIZAR COMPRA", use_container_width=True, type="primary"):
                registrar_venta(st.session_state.carrito, t_usd, tasa_dolar, t_bs)
                st.session_state.carrito = [] # Limpiamos carrito tras la venta
                st.success("Venta guardada en el historial.")
                st.rerun()
            
            # Acción para borrar sin guardar
            if st.button("🗑️ Vaciar Carrito", use_container_width=True):
                st.session_state.carrito = []
                st.rerun()
        else:
            st.info("Selecciona productos para ver la cuenta.")

# --- TAB 2: GESTIÓN DE INVENTARIO ---
with tab2:
    st.header("Administración")
    col_manual, col_csv = st.columns(2)
    
    with col_manual:
        st.subheader("✨ Agregar uno a uno")
        with st.form("form_nuevo_p", clear_on_submit=True):
            nombre = st.text_input("Nombre del producto")
            cat = st.selectbox("Categoría", ["Viveres", "Charcuteria", "Limpieza", "Hogar", "Otros"])
            precio = st.number_input("Precio en $", min_value=0.0, step=0.01)
            
            if st.form_submit_button("Guardar"):
                if nombre:
                    conn = conectar()
                    conn.execute("INSERT INTO productos (nombre, categoria, precio_usd) VALUES (?, ?, ?)", (nombre, cat, precio))
                    conn.commit()
                    conn.close()
                    st.success(f"{nombre} registrado.")
                    st.rerun()

    with col_csv:
        st.subheader("📂 Carga masiva")
        st.write("Sube un archivo .csv con columnas: **nombre, categoria, precio_usd**")
        archivo = st.file_uploader("Seleccionar CSV", type=['csv'])
        
        if archivo and st.button("Importar Productos"):
            try:
                df_import = pd.read_csv(archivo)
                conn = conectar()
                df_import.to_sql('productos', conn, if_exists='append', index=False)
                conn.close()
                st.success("Carga masiva completada.")
                st.rerun()
            except Exception as e:
                st.error(f"Error: Revisa que las columnas coincidan. {e}")

# --- TAB 3: HISTORIAL DE FACTURAS ---
with tab3:
    st.header("Facturas Guardadas")
    conn = conectar()
    # Leemos todas las ventas guardadas
    df_ventas = pd.read_sql_query("SELECT * FROM ventas ORDER BY id DESC", conn)
    conn.close()
    
    if not df_ventas.empty:
        # Renombramos las columnas para que el usuario las vea bonito
        df_ventas.columns = ["ID", "Fecha/Hora", "Lista Productos", "Total ($)", "Tasa Aplicada", "Total (Bs.)"]
        st.dataframe(df_ventas, use_container_width=True, hide_index=True)
        
        # Botón de seguridad para borrar el registro
        if st.button("⚠️ Borrar todo el Historial"):
            conn = conectar()
            conn.execute("DELETE FROM ventas")
            conn.commit()
            conn.close()
            st.rerun()
    else:
        st.info("No hay facturas registradas.")