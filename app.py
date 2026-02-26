import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

# ==========================================
# 1. CONFIGURACIÓN Y ESTILOS
# ==========================================
st.set_page_config(page_title="Sistema POS Mamá", layout="wide")

# Estilo CSS para que el carrito se vea mejor en móviles
st.markdown("""
    <style>
    .stMetric { background-color: #f0f2f6; padding: 10px; border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# 2. GESTIÓN DE BASE DE DATOS
# ==========================================
def conectar():
    return sqlite3.connect('inventario.db')

def crear_db():
    conn = conectar()
    c = conn.cursor()
    # Tabla de Productos
    c.execute('''CREATE TABLE IF NOT EXISTS productos 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT, categoria TEXT, precio_usd REAL)''')
    # Tabla de Ventas (Facturas)
    c.execute('''CREATE TABLE IF NOT EXISTS ventas 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, fecha TEXT, productos TEXT, total_usd REAL, tasa_bs REAL, total_bs REAL)''')
    # Tabla de Configuración (Tasa)
    c.execute('''CREATE TABLE IF NOT EXISTS configuracion (id INTEGER PRIMARY KEY, tasa_dolar REAL)''')
    
    # Inicializar tasa si la tabla está vacía
    c.execute("SELECT COUNT(*) FROM configuracion")
    if c.fetchone()[0] == 0:
        c.execute("INSERT INTO configuracion (id, tasa_dolar) VALUES (1, 36.5)")
    
    conn.commit()
    conn.close()

def obtener_tasa():
    conn = conectar()
    tasa = conn.execute("SELECT tasa_dolar FROM configuracion WHERE id=1").fetchone()[0]
    conn.close()
    return tasa

def actualizar_tasa(nueva_tasa):
    conn = conectar()
    conn.execute("UPDATE configuracion SET tasa_dolar = ? WHERE id=1", (nueva_tasa,))
    conn.commit()
    conn.close()

def registrar_venta(lista, t_u, tasa, t_b):
    conn = conectar()
    nombres = ", ".join([p['nombre'] for p in lista])
    fecha = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    conn.execute("INSERT INTO ventas (fecha, productos, total_usd, tasa_bs, total_bs) VALUES (?, ?, ?, ?, ?)",
                 (fecha, nombres, t_u, tasa, t_b))
    conn.commit()
    conn.close()

# Inicializar
crear_db()

# ==========================================
# 3. CONTROL DE ACCESO (LOGIN)
# ==========================================
if 'autenticado' not in st.session_state:
    st.session_state.autenticado = False
    st.session_state.rol = None

if not st.session_state.autenticado:
    st.title("🏪 Punto de Venta - Acceso")
    with st.form("login_form"):
        user = st.text_input("Usuario")
        pw = st.text_input("Contraseña", type="password")
        if st.form_submit_button("Entrar"):
            if user == "admin" and pw == "admin123":
                st.session_state.autenticado = True
                st.session_state.rol = "admin"
                st.rerun()
            elif user == "empleado" and pw == "tienda123":
                st.session_state.autenticado = True
                st.session_state.rol = "usuario"
                st.rerun()
            else:
                st.error("Credenciales incorrectas")
    st.stop()

# ==========================================
# 4. LÓGICA DE INTERFAZ
# ==========================================

# Sidebar: Información y Cierre de Sesión
st.sidebar.title(f"👤 Rol: {st.session_state.rol.capitalize()}")
tasa_actual = obtener_tasa()
st.sidebar.metric("Tasa Actual", f"{tasa_actual} Bs.")

if st.session_state.rol == "admin":
    with st.sidebar.expander("🔄 Actualizar Tasa"):
        nueva = st.number_input("Nueva Tasa", value=tasa_actual, step=0.1)
        if st.button("Guardar Tasa"):
            actualizar_tasa(nueva)
            st.rerun()

if st.sidebar.button("🚪 Cerrar Sesión"):
    st.session_state.autenticado = False
    st.rerun()

# --- PESTAÑAS SEGÚN ROL ---
if st.session_state.rol == "admin":
    tabs = st.tabs(["🛒 Ventas", "📦 Inventario", "📄 Historial"])
else:
    tabs = st.tabs(["🛒 Ventas"])

# --- TAB 1: VENTAS (Para Admin y Usuario) ---
with tabs[0]:
    if 'carrito' not in st.session_state:
        st.session_state.carrito = []

    # Carrito Flotante (Expander) al principio para evitar scroll largo en móvil
    with st.expander("🛒 VER CARRITO ACTUAL", expanded=len(st.session_state.carrito) > 0):
        if st.session_state.carrito:
            total_u = sum(p['precio_usd'] for p in st.session_state.carrito)
            total_b = total_u * tasa_actual
            
            for i, p in enumerate(st.session_state.carrito):
                st.write(f"✅ {p['nombre']} - ${p['precio_usd']:.2f}")
            
            st.divider()
            st.metric("TOTAL A COBRAR", f"{total_b:,.2f} Bs.")
            st.write(f"Total en Divisa: ${total_u:,.2f}")
            
            col_c1, col_c2 = st.columns(2)
            if col_c1.button("✅ FINALIZAR", use_container_width=True, type="primary"):
                registrar_venta(st.session_state.carrito, total_u, tasa_actual, total_b)
                st.session_state.carrito = []
                st.success("¡Venta Exitosa!")
                st.rerun()
            if col_c2.button("🗑️ VACIAR", use_container_width=True):
                st.session_state.carrito = []
                st.rerun()
        else:
            st.info("El carrito está vacío.")

    st.subheader("🔍 Buscar Productos")
    busqueda = st.text_input("Nombre del producto...")
    
    conn = conectar()
    df_p = pd.read_sql_query("SELECT * FROM productos WHERE nombre LIKE ?", conn, params=(f'%{busqueda}%',))
    conn.close()

    if not df_p.empty:
        for _, row in df_p.iterrows():
            p_bs = row['precio_usd'] * tasa_actual
            if st.button(f"{row['nombre']} | ${row['precio_usd']:.2f} ({p_bs:,.2f} Bs)", key=f"p_{row['id']}", use_container_width=True):
                st.session_state.carrito.append(row)
                st.toast(f"Agregado: {row['nombre']}")
    else:
        st.write("No se encontraron productos.")

# --- TABS SOLO PARA ADMIN ---
if st.session_state.rol == "admin":
    # TAB 2: INVENTARIO
    with tabs[1]:
        st.header("Gestión de Inventario")
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("✨ Registro Manual")
            with st.form("manual_p", clear_on_submit=True):
                nom = st.text_input("Nombre")
                cat = st.selectbox("Categoría", ["Víveres", "Charcutería", "Limpieza", "Otros"])
                pre = st.number_input("Precio $", min_value=0.0, step=0.01)
                if st.form_submit_button("Guardar"):
                    if nom:
                        conn = conectar()
                        conn.execute("INSERT INTO productos (nombre, categoria, precio_usd) VALUES (?,?,?)", (nom, cat, pre))
                        conn.commit(); conn.close()
                        st.success("Guardado")
                        st.rerun()
        with c2:
            st.subheader("📂 Carga Masiva")
            f = st.file_uploader("Subir CSV", type=['csv'])
            if f and st.button("Importar"):
                df_i = pd.read_csv(f)
                conn = conectar()
                df_i.to_sql('productos', conn, if_exists='append', index=False)
                conn.close()
                st.success("Importado")
                st.rerun()

    # TAB 3: HISTORIAL
    with tabs[2]:
        st.header("📄 Historial de Facturas")
        conn = conectar()
        df_v = pd.read_sql_query("SELECT * FROM ventas ORDER BY id DESC", conn)
        conn.close()
        
        if not df_v.empty:
            st.dataframe(df_v, use_container_width=True, hide_index=True)
            if st.button("⚠️ ELIMINAR TODO EL HISTORIAL"):
                conn = conectar()
                conn.execute("DELETE FROM ventas")
                conn.commit(); conn.close()
                st.rerun()
        else:
            st.info("No hay registros.")