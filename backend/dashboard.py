"""
Field Sales CRM — Owner Dashboard

Real-time analytics dashboard that replaces the Excel spreadsheet.
Runs on the owner's laptop at http://localhost:8501

Usage:
    cd backend
    streamlit run dashboard.py
"""
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

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

# Database path — same as FastAPI
DB_PATH = Path("C:/ventas/crm.db")


@st.cache_resource
def get_connection():
    """Persistent SQLite connection (read-only for dashboard)."""
    if not DB_PATH.exists():
        st.error(f"Database not found at {DB_PATH}. Run the backend first to create it.")
        st.stop()
    return sqlite3.connect(str(DB_PATH), check_same_thread=False)


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


# ============ BUILD WHERE CLAUSES ============

def build_date_filter(date_col: str) -> str:
    """Build date filter SQL fragment."""
    return f"{date_col} >= '{fecha_inicio}' AND {date_col} <= '{fecha_fin} 23:59:59'"


def build_rep_filter(rep_col: str) -> str:
    """Build rep filter SQL fragment."""
    rep_id = reps_options[rep_sel]
    if rep_id:
        return f" AND {rep_col} = {rep_id}"
    return ""


def build_zona_filter() -> str:
    if zona_sel != "Todas":
        return f" AND c.zona = '{zona_sel}'"
    return ""


# ============ MAIN DASHBOARD ============

st.title("📱 Dashboard de Ventas de Campo")
st.markdown(f"**{fecha_inicio.strftime('%d/%m/%Y')}** — **{fecha_fin.strftime('%d/%m/%Y')}**")

# ---- KPI ROW ----
col1, col2, col3, col4, col5 = st.columns(5)

# Total clients
total_clients = query("SELECT COUNT(*) as n FROM clientes").iloc[0]["n"]
col1.metric("👥 Clientes", f"{total_clients:,}")

# Calls in period
calls_df = query(f"""
    SELECT COUNT(*) as n FROM llamadas l
    WHERE {build_date_filter('l.fecha')}{build_rep_filter('l.vendedor_id')}
""")
col2.metric("📞 Llamadas", f"{calls_df.iloc[0]['n']:,}")

# Visits in period
visits_df = query(f"""
    SELECT COUNT(*) as n FROM visitas v
    WHERE {build_date_filter('v.fecha')}{build_rep_filter('v.vendedor_id')}
""")
col3.metric("🚗 Visitas", f"{visits_df.iloc[0]['n']:,}")

# Appointment rate
citas_df = query(f"""
    SELECT
        COUNT(*) as total,
        SUM(CASE WHEN resultado = 'cita' THEN 1 ELSE 0 END) as citas
    FROM llamadas l
    WHERE {build_date_filter('l.fecha')}{build_rep_filter('l.vendedor_id')}
""")
total_calls = citas_df.iloc[0]["total"]
total_citas = citas_df.iloc[0]["citas"]
tasa = (total_citas / total_calls * 100) if total_calls > 0 else 0
col4.metric("📅 Tasa de Citas", f"{tasa:.1f}%")

# Sales
ventas_df = query(f"""
    SELECT COUNT(*) as n FROM llamadas l
    WHERE resultado = 'venta' AND {build_date_filter('l.fecha')}{build_rep_filter('l.vendedor_id')}
""")
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
    daily_calls = query(f"""
        SELECT DATE(fecha) as dia, COUNT(*) as llamadas,
            SUM(CASE WHEN resultado = 'cita' THEN 1 ELSE 0 END) as citas,
            SUM(CASE WHEN resultado = 'venta' THEN 1 ELSE 0 END) as ventas
        FROM llamadas l
        WHERE {build_date_filter('l.fecha')}{build_rep_filter('l.vendedor_id')}
        GROUP BY DATE(fecha)
        ORDER BY dia
    """)

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
    top_reps = query(f"""
        SELECT v.nombre,
            COUNT(DISTINCT vis.id) as visitas,
            COUNT(DISTINCT l.id) as llamadas
        FROM vendedores v
        LEFT JOIN visitas vis ON vis.vendedor_id = v.id
            AND {build_date_filter('vis.fecha')}
        LEFT JOIN llamadas l ON l.vendedor_id = v.id
            AND {build_date_filter('l.fecha')}
        WHERE v.activo = 1
        GROUP BY v.id
        ORDER BY visitas DESC
        LIMIT 10
    """)

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
    results_df = query(f"""
        SELECT resultado, COUNT(*) as cantidad
        FROM llamadas l
        WHERE {build_date_filter('l.fecha')}{build_rep_filter('l.vendedor_id')}
        GROUP BY resultado
        ORDER BY cantidad DESC
    """)

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
    placeholders = ",".join(f"'{s}'" for s in status_filter)
    zona_filter = f"AND zona = '{zona_sel}'" if zona_sel != "Todas" else ""

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
        WHERE c.estado IN ({placeholders}) {zona_filter}
        ORDER BY c.updated_at DESC
        LIMIT 200
    """)

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

# ---- FOOTER ----
st.markdown("---")
st.caption("Field Sales CRM v0.1.0 | Dashboard actualizado en tiempo real desde SQLite")
