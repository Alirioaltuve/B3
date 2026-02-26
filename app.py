import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

# ==========================================
# 1. CONFIGURACIÓN Y ESTILOS
# ==========================================
st.set_page_config(page_title="Mis 3 Bendiciones C.A", layout="wide")

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
    .cart-row {
        background-color: #ffffff;
        padding: 10px;
        border-bottom: 1px solid #eee;
        border-radius: 5px;
        margin-bottom: 5px;
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
    st.title("🏪 B3 - ACCESO")
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
            else: st.error("Usuario o clave incorrecta")
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

if st.sidebar.button("🚪 Cerrar Sesión"):
    st.session_state.autenticado = False; st.rerun()

if st.session_state.rol == "admin":
    tab_ventas, tab_inventario, tab_historial = st.tabs(["🛒 Ventas", "📦 Inventario", "📄 Historial"])
else:
    tab_ventas = st.tabs(["🛒 Ventas"])[0]

# --- TAB VENTAS ---
with tab_ventas:
    with st.expander("🛒 RESUMEN DEL CARRITO", expanded=len(st.session_state.carrito) > 0):
        if st.session_state.carrito:
            total_u = 0
            ids_actuales = list(st.session_state.carrito.keys())
            
            for pid in ids_actuales:
                item = st.session_state.carrito[pid]
                sub = item['precio_usd'] * item['cantidad']
                total_u += sub
                
                # Fila de producto con controles + / -
                col_info, col_restar, col_sumar = st.columns([3, 1, 1])
                with col_info:
                    st.markdown(f"**{item['cantidad']}x** {item['nombre']} (${sub:.2f})")
                with col_restar:
                    if st.button("➖", key=f"min_{pid}", use_container_width=True):
                        st.session_state.carrito[pid]['cantidad'] -= 1
                        if st.session_state.carrito[pid]['cantidad'] <= 0:
                            del st.session_state.carrito[pid]
                        st.rerun()
                with col_sumar:
                    if st.button("➕", key=f"plus_{pid}", use_container_width=True):
                        st.session_state.carrito[pid]['cantidad'] += 1
                        st.rerun()
            
            total_b = total_u * tasa_actual
            st.divider()
            st.metric("TOTAL A PAGAR (Bs.)", f"{total_b:,.2f} Bs.")
            st.write(f"Total en Divisa: **${total_u:.2f}**")
            
            st.warning("⚠️ ¿Confirmar el cobro?")
            confirmado = st.checkbox("Monto y productos verificados")
            
            c1, c2 = st.columns(2)
            if c1.button("✅ REGISTRAR VENTA", use_container_width=True, type="primary", disabled=not confirmado):
                registrar_venta(st.session_state.carrito, total_u, tasa_actual, total_b)
                st.session_state.carrito = {}
                st.success("✨ ¡VENTA REGISTRADA! ✨")
                st.balloons()
                if st.button("Siguiente Cliente"): st.rerun()
            
            if c2.button("🗑️ VACIAR", use_container_width=True):
                st.session_state.carrito = {}
                st.rerun()
        else:
            st.info("Seleccione productos de la lista abajo.")

    st.subheader("🔍 Buscar Productos")
    busqueda = st.text_input("Escriba el nombre...")
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
                if st.form_submit_button("Guardar"):
                    if n:
                        conn = conectar(); conn.execute("INSERT INTO productos (nombre, categoria, precio_usd) VALUES (?,?,?)", (n,c,p)); conn.commit(); conn.close()
                        st.success("Guardado"); st.rerun()
        with cb:
            st.subheader("📂 Carga Masiva")
            f = st.file_uploader("Subir CSV", type=['csv'])
            if f and st.button("Importar"):
                df_i = pd.read_csv(f)
                conn = conectar(); df_i.to_sql('productos', conn, if_exists='append', index=False); conn.close()
                st.success("Importado"); st.rerun()

    with tab_historial:
        st.header("📄 Historial de Facturas")
        with st.expander("🗑️ ELIMINAR FACTURA ESPECÍFICA"):
            idx = st.number_input("ID Factura", min_value=1, step=1)
            if st.button("Borrar"):
                conn = conectar(); c = conn.cursor(); c.execute("DELETE FROM ventas WHERE id = ?", (idx,))
                if c.rowcount > 0: conn.commit(); st.success("Eliminada"); st.rerun()
                else: st.error("No existe"); conn.close()
        st.divider()
        conn = conectar()
        df_v = pd.read_sql_query("SELECT id AS ID, fecha AS Fecha, productos AS Detalle, total_usd AS 'Total $', tasa_bs AS Tasa, total_bs AS 'Total Bs' FROM ventas ORDER BY id DESC", conn)
        conn.close()
        if not df_v.empty:
            st.dataframe(df_v, use_container_width=True, hide_index=True)
            if st.button("⚠️ BORRAR TODO"):
                conn = conectar(); conn.execute("DELETE FROM ventas"); conn.commit(); conn.close()
                st.rerun()