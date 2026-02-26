import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

# ==========================================
# 1. CONFIGURACIÓN Y ESTILOS CSS
# ==========================================
st.set_page_config(page_title="Login-Mis 3 Bendiciones", layout="wide")

st.markdown("""
    <style>
    [data-testid="stMetricValue"] {
        color: #000000 !important;
        font-weight: bold !important;
        background-color: #e8f0fe;
        padding: 5px 10px;
        border-radius: 5px;
    }
    [data-testid="stMetricLabel"] {
        color: #1a237e !important;
        font-size: 1.1rem !important;
        font-weight: bold !important;
    }
    .cart-item {
        background-color: #ffffff;
        padding: 8px;
        border-bottom: 1px solid #ddd;
        color: #333;
    }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# 2. BASE DE DATOS
# ==========================================
def conectar():
    return sqlite3.connect('inventario.db')

def crear_db():
    conn = conectar()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS productos 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT, categoria TEXT, precio_usd REAL)''')
    c.execute('''CREATE TABLE IF NOT EXISTS ventas 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, fecha TEXT, productos TEXT, total_usd REAL, tasa_bs REAL, total_bs REAL)''')
    c.execute('''CREATE TABLE IF NOT EXISTS configuracion (id INTEGER PRIMARY KEY, tasa_dolar REAL)''')
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

def registrar_venta(carrito_dict, t_u, tasa, t_b):
    conn = conectar()
    detalles = ", ".join([f"{v['cantidad']}x {v['nombre']}" for v in carrito_dict.values()])
    fecha = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    conn.execute("INSERT INTO ventas (fecha, productos, total_usd, tasa_bs, total_bs) VALUES (?, ?, ?, ?, ?)",
                 (fecha, detalles, t_u, tasa, t_b))
    conn.commit()
    conn.close()

crear_db()

# ==========================================
# 3. LOGIN Y SESIÓN
# ==========================================
if 'autenticado' not in st.session_state:
    st.session_state.autenticado = False
    st.session_state.rol = None
if 'carrito' not in st.session_state:
    st.session_state.carrito = {}

if not st.session_state.autenticado:
    st.title("🏪 Mis 3 Bendiciones - Acceso")
    with st.form("login"):
        u = st.text_input("Usuario")
        p = st.text_input("Clave", type="password")
        if st.form_submit_button("Entrar"):
            if u == "haydee" and p == "paulina/17":
                st.session_state.autenticado, st.session_state.rol = True, "admin"
                st.rerun()
            elif u == "empleado" and p == "tienda123":
                st.session_state.autenticado, st.session_state.rol = True, "usuario"
                st.rerun()
            else: st.error("Credenciales incorrectas")
    st.stop()

# ==========================================
# 4. INTERFAZ
# ==========================================
st.sidebar.title(f"👤 {st.session_state.rol.upper()}")
tasa_actual = obtener_tasa()
st.sidebar.metric("TASA ACTUAL", f"{tasa_actual} Bs.")

if st.session_state.rol == "admin":
    with st.sidebar.expander("🔄 ACTUALIZAR TASA"):
        nueva = st.number_input("Nuevo valor", value=tasa_actual, step=0.1)
        if st.button("Guardar"):
            actualizar_tasa(nueva); st.rerun()

if st.sidebar.button("🚪 Salir"):
    st.session_state.autenticado = False; st.rerun()

if st.session_state.rol == "admin":
    tab_ventas, tab_inventario, tab_historial = st.tabs(["🛒 Ventas", "📦 Inventario", "📄 Historial"])
else:
    tab_ventas = st.tabs(["🛒 Ventas"])[0]

# --- TAB VENTAS ---
with tab_ventas:
    with st.expander("🛒 CARRITO", expanded=len(st.session_state.carrito) > 0):
        if st.session_state.carrito:
            total_u = 0
            for k, v in st.session_state.carrito.items():
                sub = v['precio_usd'] * v['cantidad']
                total_u += sub
                st.markdown(f"<div class='cart-item'><b>{v['cantidad']}x</b> {v['nombre']} — ${sub:.2f}</div>", unsafe_allow_html=True)
            
            total_b = total_u * tasa_actual
            st.divider()
            st.metric("TOTAL A COBRAR (Bs.)", f"{total_b:,.2f} Bs.")
            st.write(f"Total Divisa: **${total_u:.2f}**")
            
            # --- SECCIÓN DE CONFIRMACIÓN ---
            st.warning("⚠️ ¿Confirmar el cobro?")
            confirmado = st.checkbox("Sí, el monto y los productos son correctos")
            
            c1, c2 = st.columns(2)
            if c1.button("✅ REGISTRAR VENTA", use_container_width=True, type="primary", disabled=not confirmado):
                registrar_venta(st.session_state.carrito, total_u, tasa_actual, total_b)
                st.session_state.carrito = {}
                st.success("✨ ¡VENTA REGISTRADA CON ÉXITO! ✨")
                st.balloons() # Efecto visual de celebración
                # Esperamos un momento para que vean el mensaje antes de recargar
                # st.rerun() se llamará después de que el usuario interactúe de nuevo o podemos usar un botón de 'Nueva Venta'
                if st.button("🔄 Iniciar Nueva Venta"):
                    st.rerun()
            
            if c2.button("🗑️ VACIAR CARRITO", use_container_width=True):
                st.session_state.carrito = {}
                st.rerun()
        else:
            st.info("El carrito está vacío. Seleccione productos abajo.")

    st.subheader("🔍 Productos Disponibles")
    busqueda = st.text_input("Buscar por nombre...")
    conn = conectar()
    df_p = pd.read_sql_query("SELECT * FROM productos WHERE nombre LIKE ? ORDER BY nombre ASC", conn, params=(f'%{busqueda}%',))
    conn.close()

    for _, row in df_p.iterrows():
        p_bs = row['precio_usd'] * tasa_actual
        if st.button(f"{row['nombre']} | ${row['precio_usd']:.2f} ({p_bs:,.2f} Bs)", key=f"p_{row['id']}", use_container_width=True):
            pid = str(row['id'])
            if pid in st.session_state.carrito:
                st.session_state.carrito[pid]['cantidad'] += 1
            else:
                st.session_state.carrito[pid] = {'nombre': row['nombre'], 'precio_usd': row['precio_usd'], 'cantidad': 1}
            st.rerun()

# --- TABS ADMIN ---
if st.session_state.rol == "admin":
    with tab_inventario:
        st.header("Gestión de Inventario")
        ca, cb = st.columns(2)
        with ca:
            st.subheader("✨ Registro Manual")
            with st.form("manual"):
                n = st.text_input("Nombre")
                c = st.selectbox("Categoría", ["Víveres", "Charcutería", "Limpieza", "Bebidas", "Hogar", "Otros"])
                p = st.number_input("Precio $", min_value=0.0, step=0.01)
                if st.form_submit_button("Guardar Producto"):
                    if n:
                        conn = conectar(); conn.execute("INSERT INTO productos (nombre, categoria, precio_usd) VALUES (?,?,?)", (n,c,p)); conn.commit(); conn.close()
                        st.success(f"✅ {n} guardado correctamente."); st.rerun()
        with cb:
            st.subheader("📂 Carga Masiva")
            f = st.file_uploader("Subir CSV", type=['csv'])
            if f and st.button("Importar Ahora"):
                df_i = pd.read_csv(f)
                conn = conectar(); df_i.to_sql('productos', conn, if_exists='append', index=False); conn.close()
                st.success("✅ Productos importados con éxito."); st.rerun()

    with tab_historial:
        st.header("📄 Historial de Facturas")
        
        with st.expander("🗑️ ELIMINAR FACTURA ESPECÍFICA"):
            id_a_eliminar = st.number_input("ID de la factura", min_value=1, step=1)
            if st.button("Borrar Factura"):
                conn = conectar()
                cursor = conn.cursor()
                cursor.execute("DELETE FROM ventas WHERE id = ?", (id_a_eliminar,))
                if cursor.rowcount > 0:
                    conn.commit()
                    st.success(f"Factura #{id_a_eliminar} eliminada.")
                    conn.close()
                    st.rerun()
                else:
                    st.error("No se encontró esa ID.")
                    conn.close()

        st.divider()
        conn = conectar()
        df_v = pd.read_sql_query("SELECT id AS ID, fecha AS Fecha, productos AS Detalle, total_usd AS 'Total $', tasa_bs AS Tasa, total_bs AS 'Total Bs' FROM ventas ORDER BY id DESC", conn)
        conn.close()
        
        if not df_v.empty:
            st.dataframe(df_v, use_container_width=True, hide_index=True)
            if st.button("⚠️ BORRAR TODO EL HISTORIAL"):
                conn = conectar(); conn.execute("DELETE FROM ventas"); conn.commit(); conn.close()
                st.success("Historial limpiado."); st.rerun()
        else:
            st.info("No hay facturas registradas.")