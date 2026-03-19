"""
Field Sales CRM — Owner Dashboard

Real-time analytics dashboard that replaces the Excel spreadsheet.
Runs on the owner's laptop at http://localhost:8501

Usage:
    cd backend
    streamlit run dashboard.py
"""
import secrets
import sqlite3
import string
from datetime import datetime
from pathlib import Path

from passlib.context import CryptContext

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# ============ CONFIG ============

st.set_page_config(
    page_title="Field Sales CRM",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Database path — same as FastAPI (Fly.io persistent volume)
DB_PATH = Path("/data/crm.db")

# ============ DASHBOARD AUTHENTICATION ============

import os as _os
_DASHBOARD_PASSWORD = _os.environ.get("DASHBOARD_PASSWORD", "")

if _DASHBOARD_PASSWORD:
    if not st.session_state.get("dash_authenticated"):
        st.title("🔐 Field Sales CRM")
        _pwd = st.text_input("Contraseña del dashboard", type="password")
        if st.button("Entrar", use_container_width=True):
            if _pwd == _DASHBOARD_PASSWORD:
                st.session_state["dash_authenticated"] = True
                st.rerun()
            else:
                st.error("Contraseña incorrecta.")
        st.stop()

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def generate_password(length: int = 10) -> str:
    chars = string.ascii_letters + string.digits
    return ''.join(secrets.choice(chars) for _ in range(length))


@st.cache_resource
def get_connection():
    """Persistent SQLite connection (read-only for dashboard)."""
    if not DB_PATH.exists():
        st.error(f"Database not found at {DB_PATH}. Run the backend first to create it.")
        st.stop()
    return sqlite3.connect(str(DB_PATH), check_same_thread=False)


def write_db(sql: str, params: tuple = ()):
    """Execute a write query on a fresh connection."""
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.execute(sql, params)
    conn.commit()
    conn.close()


def query(sql: str, params: tuple = ()) -> pd.DataFrame:
    """Execute SQL and return DataFrame."""
    conn = get_connection()
    return pd.read_sql_query(sql, conn, params=params)


# ============ SIDEBAR ============

st.sidebar.title("📊 Field Sales CRM")
st.sidebar.markdown("---")

# Date range filter
st.sidebar.subheader("Filtros")
fecha_inicio = st.sidebar.date_input(
    "Desde",
    value=datetime.now().replace(day=1).date(),
)
fecha_fin = st.sidebar.date_input(
    "Hasta",
    value=datetime.now().date(),
)

# Zone filter
zonas_df = query("SELECT DISTINCT zona FROM clientes WHERE zona IS NOT NULL ORDER BY zona")
zonas = ["Todas"] + zonas_df["zona"].tolist()
zona_sel = st.sidebar.selectbox("Zona", zonas)

# Rep filter
reps_df = query("SELECT id, nombre FROM vendedores WHERE activo = 1 ORDER BY nombre")
reps_options = {"Todos": None}
for _, row in reps_df.iterrows():
    reps_options[row["nombre"]] = row["id"]
rep_sel = st.sidebar.selectbox("Vendedor", list(reps_options.keys()))

# Refresh button
if st.sidebar.button("🔄 Actualizar datos", use_container_width=True):
    st.cache_resource.clear()
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.caption(f"Base de datos: {DB_PATH}")
st.sidebar.caption(f"Última actualización: {datetime.now().strftime('%H:%M:%S')}")


# ============ BUILD WHERE CLAUSES (parameterized — no SQL injection) ============

def build_filters(date_col: str, rep_col: str = None, zona_col: str = None):
    """Return (where_clause, params_tuple) using ? placeholders."""
    conditions = [f"{date_col} >= ? AND {date_col} <= ?"]
    params = [str(fecha_inicio), f"{fecha_fin} 23:59:59"]

    if rep_col:
        rep_id = reps_options[rep_sel]
        if rep_id:
            conditions.append(f"{rep_col} = ?")
            params.append(rep_id)

    if zona_col and zona_sel != "Todas":
        conditions.append(f"{zona_col} = ?")
        params.append(zona_sel)

    return " AND ".join(conditions), tuple(params)


# ============ MAIN DASHBOARD ============

st.title("📱 Dashboard de Ventas de Campo")
st.markdown(f"**{fecha_inicio.strftime('%d/%m/%Y')}** — **{fecha_fin.strftime('%d/%m/%Y')}**")

# ---- KPI ROW ----
col1, col2, col3, col4, col5 = st.columns(5)

# Total clients
total_clients = query("SELECT COUNT(*) as n FROM clientes").iloc[0]["n"]
col1.metric("👥 Clientes", f"{total_clients:,}")

# Calls in period
_where, _params = build_filters('l.fecha', rep_col='l.vendedor_id')
calls_df = query(f"SELECT COUNT(*) as n FROM llamadas l WHERE {_where}", _params)
col2.metric("📞 Llamadas", f"{calls_df.iloc[0]['n']:,}")

# Visits in period
_where, _params = build_filters('v.fecha', rep_col='v.vendedor_id')
visits_df = query(f"SELECT COUNT(*) as n FROM visitas v WHERE {_where}", _params)
col3.metric("🚗 Visitas", f"{visits_df.iloc[0]['n']:,}")

# Appointment rate
_where, _params = build_filters('l.fecha', rep_col='l.vendedor_id')
citas_df = query(f"""
    SELECT COUNT(*) as total,
        SUM(CASE WHEN resultado = 'cita' THEN 1 ELSE 0 END) as citas
    FROM llamadas l WHERE {_where}
""", _params)
total_calls = citas_df.iloc[0]["total"]
total_citas = citas_df.iloc[0]["citas"]
tasa = (total_citas / total_calls * 100) if total_calls > 0 else 0
col4.metric("📅 Tasa de Citas", f"{tasa:.1f}%")

# Sales
_where, _params = build_filters('l.fecha', rep_col='l.vendedor_id')
ventas_df = query(
    f"SELECT COUNT(*) as n FROM llamadas l WHERE resultado = 'venta' AND {_where}",
    _params,
)
col5.metric("💰 Ventas", f"{ventas_df.iloc[0]['n']:,}")

st.markdown("---")

# ---- CHARTS ROW 1 ----
chart_col1, chart_col2 = st.columns(2)

# Chart 1: Clients by status (pie chart — replaces Excel color legend)
with chart_col1:
    st.subheader("Estado de Clientes")
    status_df = query("""
        SELECT estado, COUNT(*) as cantidad FROM clientes
        GROUP BY estado ORDER BY cantidad DESC
    """)

    if not status_df.empty:
        color_map = {
            "no_llamar": "#ef4444",
            "venta": "#10b981",
            "equivocado": "#eab308",
            "cita": "#a855f7",
            "seguimiento": "#3b82f6",
            "nuevo": "#94a3b8",
        }
        status_df["color"] = status_df["estado"].map(color_map).fillna("#94a3b8")

        fig = px.pie(
            status_df, values="cantidad", names="estado",
            color="estado", color_discrete_map=color_map,
            hole=0.4,
        )
        fig.update_layout(
            margin=dict(t=20, b=20, l=20, r=20),
            height=350,
            font=dict(size=13),
        )
        st.plotly_chart(fig, use_container_width=True)

# Chart 2: Calls per day (bar chart)
with chart_col2:
    st.subheader("Llamadas por Día")
    _where, _params = build_filters('l.fecha', rep_col='l.vendedor_id')
    daily_calls = query(f"""
        SELECT DATE(fecha) as dia, COUNT(*) as llamadas,
            SUM(CASE WHEN resultado = 'cita' THEN 1 ELSE 0 END) as citas,
            SUM(CASE WHEN resultado = 'venta' THEN 1 ELSE 0 END) as ventas
        FROM llamadas l WHERE {_where}
        GROUP BY DATE(fecha) ORDER BY dia
    """, _params)

    if not daily_calls.empty:
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=daily_calls["dia"], y=daily_calls["llamadas"],
            name="Llamadas", marker_color="#64748b",
        ))
        fig.add_trace(go.Bar(
            x=daily_calls["dia"], y=daily_calls["citas"],
            name="Citas", marker_color="#a855f7",
        ))
        fig.add_trace(go.Bar(
            x=daily_calls["dia"], y=daily_calls["ventas"],
            name="Ventas", marker_color="#10b981",
        ))
        fig.update_layout(
            barmode="overlay", height=350,
            margin=dict(t=20, b=20, l=20, r=20),
            legend=dict(orientation="h", yanchor="bottom", y=1.02),
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No hay llamadas en este período.")

# ---- CHARTS ROW 2 ----
chart_col3, chart_col4 = st.columns(2)

# Chart 3: Top sales reps
with chart_col3:
    st.subheader("🏆 Top Vendedores")
    _date_w = "vis.fecha >= ? AND vis.fecha <= ?"
    _date_p = (str(fecha_inicio), f"{fecha_fin} 23:59:59")
    _date_w2 = "l.fecha >= ? AND l.fecha <= ?"
    top_reps = query(f"""
        SELECT v.nombre,
            COUNT(DISTINCT vis.id) as visitas,
            COUNT(DISTINCT l.id) as llamadas
        FROM vendedores v
        LEFT JOIN visitas vis ON vis.vendedor_id = v.id AND {_date_w}
        LEFT JOIN llamadas l ON l.vendedor_id = v.id AND {_date_w2}
        WHERE v.activo = 1
        GROUP BY v.id ORDER BY visitas DESC LIMIT 10
    """, _date_p + _date_p)

    if not top_reps.empty:
        fig = go.Figure()
        fig.add_trace(go.Bar(
            y=top_reps["nombre"], x=top_reps["visitas"],
            name="Visitas", orientation="h", marker_color="#a855f7",
        ))
        fig.add_trace(go.Bar(
            y=top_reps["nombre"], x=top_reps["llamadas"],
            name="Llamadas", orientation="h", marker_color="#3b82f6",
        ))
        fig.update_layout(
            barmode="group", height=350,
            margin=dict(t=20, b=20, l=20, r=20),
            yaxis=dict(autorange="reversed"),
            legend=dict(orientation="h", yanchor="bottom", y=1.02),
        )
        st.plotly_chart(fig, use_container_width=True)

# Chart 4: Call results breakdown
with chart_col4:
    st.subheader("Resultados de Llamadas")
    _where, _params = build_filters('l.fecha', rep_col='l.vendedor_id')
    results_df = query(f"""
        SELECT resultado, COUNT(*) as cantidad
        FROM llamadas l WHERE {_where}
        GROUP BY resultado ORDER BY cantidad DESC
    """, _params)

    if not results_df.empty:
        result_colors = {
            "cita": "#a855f7", "no_cita": "#94a3b8", "no_contesta": "#f59e0b",
            "equivocado": "#eab308", "no_llamar": "#ef4444", "venta": "#10b981",
        }
        results_df["color"] = results_df["resultado"].map(result_colors).fillna("#64748b")

        fig = px.bar(
            results_df, x="resultado", y="cantidad",
            color="resultado", color_discrete_map=result_colors,
        )
        fig.update_layout(
            height=350, showlegend=False,
            margin=dict(t=20, b=20, l=20, r=20),
        )
        st.plotly_chart(fig, use_container_width=True)

st.markdown("---")

# ---- CLIENT TABLE (replaces Excel) ----
st.subheader("📋 Tabla de Clientes")
st.caption("Esta tabla reemplaza la hoja de Excel. Los datos se actualizan automáticamente desde la app.")

# Status filter for table
status_filter = st.multiselect(
    "Filtrar por estado:",
    options=["nuevo", "cita", "seguimiento", "venta", "no_llamar", "equivocado"],
    default=["cita", "seguimiento", "nuevo"],
)

if status_filter:
    _in_placeholders = ",".join(["?"] * len(status_filter))
    _table_params = list(status_filter)
    _zona_condition = ""
    if zona_sel != "Todas":
        _zona_condition = " AND c.zona = ?"
        _table_params.append(zona_sel)

    clients_table = query(f"""
        SELECT
            c.id as 'N°',
            c.nombre_apellido as 'Nombre y Apellido',
            c.telefono as 'Teléfono',
            c.fuente as 'Fuente',
            c.zona as 'Zona',
            c.direccion as 'Dirección',
            c.estado as 'Estado',
            (SELECT notas_vendedor FROM visitas WHERE cliente_id = c.id
             ORDER BY fecha DESC LIMIT 1) as 'Notas del Vendedor',
            (SELECT notas_telemarketing FROM llamadas WHERE cliente_id = c.id
             ORDER BY fecha DESC LIMIT 1) as 'Notas Telemarketing',
            (SELECT resultados FROM visitas WHERE cliente_id = c.id
             ORDER BY fecha DESC LIMIT 1) as 'Resultados',
            c.updated_at as 'Última Actualización'
        FROM clientes c
        WHERE c.estado IN ({_in_placeholders}){_zona_condition}
        ORDER BY c.updated_at DESC LIMIT 200
    """, tuple(_table_params))

    if not clients_table.empty:
        # Color-code the status column like the original Excel
        def color_status(val):
            colors = {
                "no_llamar": "background-color: #fee2e2; color: #991b1b",
                "venta": "background-color: #d1fae5; color: #065f46",
                "equivocado": "background-color: #fef9c3; color: #854d0e",
                "cita": "background-color: #f3e8ff; color: #6b21a8",
                "seguimiento": "background-color: #dbeafe; color: #1e40af",
                "nuevo": "background-color: #f1f5f9; color: #475569",
            }
            return colors.get(val, "")

        styled = clients_table.style.map(
            color_status, subset=["Estado"]
        )
        st.dataframe(styled, use_container_width=True, height=500)

        # Export to Excel button
        st.download_button(
            label="📥 Exportar a Excel",
            data=clients_table.to_csv(index=False).encode("utf-8-sig"),
            file_name=f"clientes_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv",
        )
    else:
        st.info("No hay clientes con los filtros seleccionados.")

st.markdown("---")

# ---- RECENT VISITS WITH TRANSCRIPTIONS ----
st.subheader("🎙️ Últimas Visitas Transcritas")

recent_visits = query(f"""
    SELECT
        v.fecha as 'Fecha',
        ve.nombre as 'Vendedor',
        c.nombre_apellido as 'Cliente',
        v.notas_vendedor as 'Notas',
        v.resultados as 'Resultado',
        v.nivel_interes as 'Interés',
        v.siguiente_paso as 'Siguiente Paso',
        v.estado_sugerido as 'Estado Sugerido'
    FROM visitas v
    JOIN vendedores ve ON v.vendedor_id = ve.id
    JOIN clientes c ON v.cliente_id = c.id
    WHERE v.procesado = 1
    ORDER BY v.fecha DESC
    LIMIT 20
""")

if not recent_visits.empty:
    st.dataframe(recent_visits, use_container_width=True, height=400)
else:
    st.info("No hay visitas transcritas aún. Las transcripciones aparecerán aquí automáticamente.")

st.markdown("---")

# ---- HISTORIAL DE CLIENTE ----
st.subheader("📁 Historial de Cliente")

all_clients = query("SELECT id, nombre_apellido, telefono FROM clientes ORDER BY nombre_apellido")
client_options = {"— Seleccionar cliente —": None}
for _, row in all_clients.iterrows():
    client_options[f"{row['nombre_apellido']} ({row['telefono']})"] = row["id"]

selected_client_label = st.selectbox("Cliente:", list(client_options.keys()))
selected_client_id = client_options[selected_client_label]

if selected_client_id:
    hist_tab_visits, hist_tab_calls = st.tabs(["🚗 Visitas", "📞 Llamadas"])

    with hist_tab_visits:
        visits_hist = query(f"""
            SELECT
                v.fecha as 'Fecha',
                ve.nombre as 'Vendedor',
                v.notas_vendedor as 'Notas',
                v.resultados as 'Resultado',
                v.nivel_interes as 'Interés',
                v.siguiente_paso as 'Siguiente Paso',
                v.estado_sugerido as 'Estado Sugerido',
                v.objeciones as 'Objeciones',
                v.transcripcion as 'Transcripción'
            FROM visitas v
            JOIN vendedores ve ON v.vendedor_id = ve.id
            WHERE v.cliente_id = {selected_client_id}
            ORDER BY v.fecha DESC
        """)
        if not visits_hist.empty:
            st.caption(f"{len(visits_hist)} visita(s) registrada(s)")
            st.dataframe(visits_hist, use_container_width=True)
            st.markdown("")
            if st.button("🗑️ Eliminar todo el historial de visitas", key="del_visits", type="primary"):
                audio_paths = query(f"SELECT audio_path FROM visitas WHERE cliente_id = {selected_client_id} AND audio_path IS NOT NULL")
                for _, row in audio_paths.iterrows():
                    try:
                        Path(row["audio_path"]).unlink(missing_ok=True)
                    except Exception:
                        pass
                write_db("DELETE FROM visitas WHERE cliente_id = ?", (selected_client_id,))
                st.success("Historial de visitas eliminado.")
                st.cache_resource.clear()
                st.rerun()
        else:
            st.info("Sin visitas registradas para este cliente.")

    with hist_tab_calls:
        calls_hist = query(f"""
            SELECT
                l.fecha as 'Fecha',
                ve.nombre as 'Vendedor',
                l.resultado as 'Resultado',
                l.duracion_seg as 'Duración (seg)',
                l.notas_telemarketing as 'Notas'
            FROM llamadas l
            JOIN vendedores ve ON l.vendedor_id = ve.id
            WHERE l.cliente_id = {selected_client_id}
            ORDER BY l.fecha DESC
        """)
        if not calls_hist.empty:
            st.caption(f"{len(calls_hist)} llamada(s) registrada(s)")
            st.dataframe(calls_hist, use_container_width=True)
            st.markdown("")
            if st.button("🗑️ Eliminar todo el historial de llamadas", key="del_calls", type="primary"):
                write_db("DELETE FROM llamadas WHERE cliente_id = ?", (selected_client_id,))
                st.success("Historial de llamadas eliminado.")
                st.cache_resource.clear()
                st.rerun()
        else:
            st.info("Sin llamadas registradas para este cliente.")

st.markdown("---")

# ---- GESTIÓN DE VENDEDORES ----
st.subheader("👥 Gestión de Vendedores")

active_reps_df = query("SELECT id, nombre, telefono, zona, created_at FROM vendedores WHERE activo = 1 ORDER BY nombre")
if not active_reps_df.empty:
    st.dataframe(active_reps_df.rename(columns={
        "id": "ID", "nombre": "Nombre", "telefono": "Teléfono",
        "zona": "Zona", "created_at": "Creado",
    }), use_container_width=True, hide_index=True)
else:
    st.info("No hay vendedores activos.")

mgmt_col1, mgmt_col2, mgmt_col3 = st.columns(3)

# --- Nuevo vendedor ---
with mgmt_col1:
    with st.expander("➕ Nuevo Vendedor"):
        with st.form("form_nuevo_vendedor"):
            nv_nombre = st.text_input("Nombre completo", key="nv_nombre")
            nv_telefono = st.text_input("Teléfono", key="nv_telefono")
            nv_zona = st.text_input("Zona (opcional)", key="nv_zona")
            nv_password = st.text_input("Contraseña inicial", type="password", key="nv_password")
            nv_submit = st.form_submit_button("Crear", use_container_width=True)

        if nv_submit:
            if nv_nombre and nv_telefono and nv_password:
                if len(nv_password) < 6:
                    st.error("La contraseña debe tener al menos 6 caracteres.")
                else:
                    existing = query("SELECT id FROM vendedores WHERE telefono = ?", (nv_telefono,))
                    if not existing.empty:
                        st.error("Ya existe un vendedor con ese teléfono.")
                    else:
                        write_db(
                            "INSERT INTO vendedores (nombre, telefono, zona, password_hash, activo, created_at) VALUES (?, ?, ?, ?, 1, ?)",
                            (nv_nombre, nv_telefono, nv_zona or None, hash_password(nv_password), datetime.utcnow()),
                        )
                        st.success(f"Vendedor '{nv_nombre}' creado.")
                        for k in ["nv_nombre", "nv_telefono", "nv_zona", "nv_password"]:
                            st.session_state.pop(k, None)
                        st.cache_resource.clear()
                        st.rerun()
            else:
                st.warning("Nombre, teléfono y contraseña son obligatorios.")

# --- Eliminar vendedor ---
with mgmt_col2:
    with st.expander("🗑️ Eliminar Vendedor"):
        if not active_reps_df.empty:
            del_options = {f"{r['nombre']} ({r['telefono']})": r["id"] for _, r in active_reps_df.iterrows()}
            del_sel = st.selectbox("Vendedor:", list(del_options.keys()), key="del_sel")
            st.warning("Esto desactiva al vendedor. Sus datos históricos se conservan.")
            if st.button("Desactivar", type="primary", use_container_width=True):
                write_db("UPDATE vendedores SET activo = 0 WHERE id = ?", (del_options[del_sel],))
                st.success("Vendedor desactivado.")
                st.cache_resource.clear()
                st.rerun()
        else:
            st.info("No hay vendedores activos.")

# --- Resetear password ---
with mgmt_col3:
    with st.expander("🔑 Resetear Password"):
        if not active_reps_df.empty:
            reset_options = {f"{r['nombre']} ({r['telefono']})": r["id"] for _, r in active_reps_df.iterrows()}
            reset_sel = st.selectbox("Vendedor:", list(reset_options.keys()), key="reset_sel")
            if st.button("Generar nueva contraseña", use_container_width=True):
                new_pass = generate_password()
                write_db(
                    "UPDATE vendedores SET password_hash = ? WHERE id = ?",
                    (hash_password(new_pass), reset_options[reset_sel]),
                )
                st.success("Nueva contraseña generada:")
                st.code(new_pass, language=None)
                st.caption("Comunica esta contraseña al vendedor. Solo se muestra una vez.")
        else:
            st.info("No hay vendedores activos.")

# ---- GESTIÓN DE CLIENTES ----
st.markdown("---")
st.subheader("👤 Gestión de Clientes")

gc_col1, gc_col2 = st.columns(2)

# --- Nuevo cliente individual ---
with gc_col1:
    with st.expander("➕ Nuevo Cliente"):
        with st.form("form_nuevo_cliente"):
            nc_nombre = st.text_input("Nombre y Apellido", key="nc_nombre")
            nc_telefono = st.text_input("Teléfono", key="nc_telefono")
            nc_zona = st.text_input("Zona (opcional)", key="nc_zona")
            nc_fuente = st.text_input("Fuente (opcional)", key="nc_fuente")
            nc_direccion = st.text_input("Dirección (opcional)", key="nc_direccion")
            nc_estado = st.selectbox(
                "Estado inicial",
                ["nuevo", "cita", "seguimiento", "venta", "no_llamar", "equivocado"],
                key="nc_estado",
            )
            nc_submit = st.form_submit_button("Crear Cliente", use_container_width=True)

        if nc_submit:
            if nc_nombre and nc_telefono:
                existing = query("SELECT id FROM clientes WHERE telefono = ?", (nc_telefono,))
                if not existing.empty:
                    st.error("Ya existe un cliente con ese teléfono.")
                else:
                    write_db(
                        """INSERT INTO clientes
                           (nombre_apellido, telefono, zona, fuente, direccion, estado, created_at, updated_at)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                        (nc_nombre, nc_telefono, nc_zona or None, nc_fuente or None,
                         nc_direccion or None, nc_estado, datetime.utcnow(), datetime.utcnow()),
                    )
                    st.success(f"Cliente '{nc_nombre}' creado.")
                    for k in ["nc_nombre", "nc_telefono", "nc_zona", "nc_fuente", "nc_direccion"]:
                        st.session_state.pop(k, None)
                    st.cache_resource.clear()
                    st.rerun()
            else:
                st.warning("Nombre y teléfono son obligatorios.")

# --- Importar desde CSV / Excel ---
with gc_col2:
    with st.expander("📂 Importar CSV / Excel"):
        st.caption("Acepta archivos CSV o Excel. Detecta automáticamente el formato y los nombres de columnas.")
        uploaded = st.file_uploader("Seleccionar archivo", type=["csv", "xlsx", "xls", "xlxs"])

        # Column name aliases — maps common variations to standard field names
        _COL_ALIASES = {
            "nombre_apellido":  ["nombre_apellido", "nombre y apellido", "nombre", "nombre_y_apellido", "name"],
            "telefono":         ["telefono", "teléfono", "telefono", "phone", "tel"],
            "zona":             ["zona", "zone"],
            "fuente":           ["fuente", "source", "origen"],
            "direccion":        ["direccion", "dirección", "address", "dir"],
        }

        def _normalize(text: str) -> str:
            """Lowercase, strip accents, replace spaces with underscores."""
            import unicodedata
            text = unicodedata.normalize("NFD", str(text))
            text = "".join(c for c in text if unicodedata.category(c) != "Mn")
            return text.strip().lower().replace(" ", "_")

        def _find_col(columns, field):
            """Return the actual column name that matches a field alias."""
            norm_cols = {_normalize(c): c for c in columns}
            for alias in _COL_ALIASES[field]:
                key = _normalize(alias)
                if key in norm_cols:
                    return norm_cols[key]
            return None

        def _find_header_row(raw_df):
            """Scan rows to find which one contains name/phone headers."""
            for i, row in raw_df.iterrows():
                vals = [_normalize(str(v)) for v in row.values if str(v) != "nan"]
                has_name  = any(a in vals for a in [_normalize(a) for a in _COL_ALIASES["nombre_apellido"]])
                has_phone = any(a in vals for a in [_normalize(a) for a in _COL_ALIASES["telefono"]])
                if has_name and has_phone:
                    return i
            return None

        def _clean(val):
            s = str(val).strip()
            return None if s in ("", "nan", "None") else s

        if uploaded:
            try:
                fname = uploaded.name.lower()
                if fname.endswith(".csv"):
                    raw = pd.read_excel(uploaded, header=None, dtype=str) if False else \
                          pd.read_csv(uploaded, dtype=str, header=None)
                else:
                    raw = pd.read_excel(uploaded, header=None, dtype=str)

                # Auto-detect header row
                header_row = _find_header_row(raw)
                if header_row is None:
                    st.error("No se encontraron columnas de nombre/teléfono en el archivo.")
                else:
                    df = pd.read_excel(uploaded, header=header_row, dtype=str) \
                         if not fname.endswith(".csv") else \
                         pd.read_csv(uploaded, header=header_row, dtype=str)

                    col_nombre   = _find_col(df.columns, "nombre_apellido")
                    col_telefono = _find_col(df.columns, "telefono")
                    col_zona     = _find_col(df.columns, "zona")
                    col_fuente   = _find_col(df.columns, "fuente")
                    col_direccion= _find_col(df.columns, "direccion")

                    if not col_nombre or not col_telefono:
                        st.error(f"No se encontraron columnas de nombre o teléfono. Columnas detectadas: {list(df.columns)}")
                    else:
                        st.success(f"Columnas detectadas — Nombre: `{col_nombre}` | Teléfono: `{col_telefono}`")
                        preview = df[[c for c in [col_nombre, col_telefono, col_zona, col_fuente, col_direccion] if c]].head(5)
                        st.dataframe(preview, use_container_width=True)
                        st.caption(f"{len(df)} filas en total")

                        if st.button("📥 Importar clientes", use_container_width=True):
                            created = 0
                            skipped = 0
                            for _, row in df.iterrows():
                                nombre   = _clean(row.get(col_nombre, ""))
                                telefono = _clean(row.get(col_telefono, ""))
                                if not nombre or not telefono:
                                    skipped += 1
                                    continue
                                existing = query("SELECT id FROM clientes WHERE telefono = ?", (telefono,))
                                if not existing.empty:
                                    skipped += 1
                                    continue
                                write_db(
                                    """INSERT INTO clientes
                                       (nombre_apellido, telefono, zona, fuente, direccion, estado, created_at, updated_at)
                                       VALUES (?, ?, ?, ?, ?, 'nuevo', ?, ?)""",
                                    (nombre, telefono,
                                     _clean(row.get(col_zona, "")) if col_zona else None,
                                     _clean(row.get(col_fuente, "")) if col_fuente else None,
                                     _clean(row.get(col_direccion, "")) if col_direccion else None,
                                     datetime.utcnow(), datetime.utcnow()),
                                )
                                created += 1
                            st.success(f"✅ {created} clientes importados. {skipped} omitidos (ya existían o sin datos).")
                            st.cache_resource.clear()
                            st.rerun()
            except Exception as e:
                st.error(f"Error al leer el archivo: {e}")

# ---- FOOTER ----
st.markdown("---")
st.caption("Field Sales CRM v0.1.0 | Dashboard actualizado en tiempo real desde SQLite")
