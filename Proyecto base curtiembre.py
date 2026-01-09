import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os

# 1. Configuración de página
st.set_page_config(page_title="Gestión Curtiembre", layout="wide")

# --- CONEXIÓN A GOOGLE SHEETS (Versión Dual: Web y Local) ---
def conectar_google_sheets():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    try:
        # 1. Intentamos leer desde los Secrets de Streamlit (Para cuando está ONLINE)
        if "gcp_service_account" in st.secrets:
            creds_dict = dict(st.secrets["gcp_service_account"])
            # Corregimos el formato de la clave privada para que Python la entienda
            creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
            creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        else:
            # 2. Si no hay secrets, usamos el archivo local (Para cuando lo usás vos en TU PC)
            creds = ServiceAccountCredentials.from_json_keyfile_name("creed.json", scope)
            
        client = gspread.authorize(creds)
        spreadsheet = client.open("pendientes")
        return spreadsheet.get_worksheet(0)
    except Exception as e:
        st.error(f"Error de conexión: {e}")
        return None

# --- ESTILO CSS AVANZADO ---

st.markdown("""
    <style>
    .block-container { padding-top: 0.5rem; padding-bottom: 0rem; }
    [data-testid="stSidebarHeader"] { padding: 0.5rem; }
    .stSidebar img { display: block; margin: auto; width: 80%; padding-top: 1rem; }
    [data-testid="stMetricValue"] { font-size: 1.5rem !important; }
    [data-testid="stMetricLabel"] { font-size: 0.8rem !important; }
    .titulo-compacto {
        text-align: left;
        font-size: 1.4rem !important;
        font-weight: bold;
        color: #1E3A8A;
        margin-bottom: 0.2rem;
        border-left: 5px solid #1E3A8A;
        padding-left: 10px;
    }
    .subtitulo-contadores {
        font-size: 1.1rem;
        font-weight: bold;
        color: #475569;
        margin-top: 0.5rem;
        border-bottom: 1px solid #e2e8f0;
        padding-bottom: 5px;
        width: 100%;
        margin-bottom: 10px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. CARGAR DATOS ---
if 'hoja' not in st.session_state:
    st.session_state.hoja = conectar_google_sheets()

def cargar_datos():
    if st.session_state.hoja:
        datos = st.session_state.hoja.get_all_records()
        df = pd.DataFrame(datos)
        df.columns = df.columns.str.strip()
        return df
    return pd.DataFrame()

if 'df_maestro' not in st.session_state:
    st.session_state.df_maestro = cargar_datos()

# --- 3. DETECTOR DE COLUMNAS ---
df = st.session_state.df_maestro
if not df.empty:
    cols = df.columns.tolist()
    def encontrar_col(nombres):
        for n in nombres:
            for c in cols:
                if n.upper() in c.upper(): return c
        return None

    COL_TEMA = encontrar_col(["TEMA", "TAREA"])
    COL_DESARROLLO = encontrar_col(["DESARROLLO", "DETALLE"])
    COL_IMPORTANCIA = encontrar_col(["IMPORTANCIA", "PRIORIDAD"])
    COL_RESPONSABLE = encontrar_col(["RESPONSABLE"])
    COL_OK = encontrar_col(["OK", "ESTADO"])

    # --- 4. BARRA LATERAL ---
    with st.sidebar:
        if os.path.exists("logo.png"): st.image("logo.png")
        st.markdown("### ⚙️ Configuración")
        responsable = st.selectbox("👤 Responsable", options=sorted(df[COL_RESPONSABLE].unique()))
        prioridades = st.multiselect("📊 Ver Prioridades", options=sorted(df[COL_IMPORTANCIA].unique()), default=sorted(df[COL_IMPORTANCIA].unique()))
        if os.path.exists("logo1.png"): st.image("logo1.png")

    # --- 5. PROCESAR VISTA ---
    df_temp = df.copy()
    # Normalizamos el OK para que el checkbox funcione
    df_temp[COL_OK] = df_temp[COL_OK].apply(lambda x: True if str(x).upper() == "OK" else False)
    mask = (df_temp[COL_RESPONSABLE] == responsable) & (df_temp[COL_IMPORTANCIA].isin(prioridades))
    df_vista = df_temp[mask][[COL_TEMA, COL_DESARROLLO, COL_IMPORTANCIA, COL_OK]].copy()

    # --- 6. PANEL SUPERIOR Y TABLA ---
    st.markdown(f'<div class="titulo-compacto">Pendientes: {responsable}</div>', unsafe_allow_html=True)
    st.markdown('<div class="subtitulo-contadores">Listado de pendientes</div>', unsafe_allow_html=True)
    
    # Marcador de posición para las métricas (para que se actualicen después de la tabla)
    contenedor_metricas = st.container()

    st.markdown("---")

    # TABLA DE DATOS (Se define antes para captar el cambio)
    df_editado = st.data_editor(
        df_vista,
        column_config={
            COL_OK: st.column_config.CheckboxColumn("OK", width="small"),
            COL_IMPORTANCIA: st.column_config.TextColumn("Prioridad", width="small"),
            COL_TEMA: st.column_config.TextColumn("Tema", width="medium"),
            COL_DESARROLLO: st.column_config.TextColumn("Desarrollo / Detalle de la tarea", width="large")
        },
        disabled=[COL_TEMA, COL_DESARROLLO, COL_IMPORTANCIA],
        hide_index=True,
        use_container_width=True,
        key="editor_tareas" # Clave para rastrear cambios
    )

    # RE-CALCULAR MÉTRICAS BASADO EN LA EDICIÓN
    def filtrar_contar_editado(pri, ok_val):
        return len(df_editado[(df_editado[COL_IMPORTANCIA].str.contains(pri, case=False, na=False)) & (df_editado[COL_OK] == ok_val)])

    with contenedor_metricas:
        col_met1, col_met2, col_met3, col_met4, col_met5, col_met6, col_vac = st.columns([1,1,1,1,1,1,3])
        col_met1.metric("Crit. ⏳", filtrar_contar_editado("Crit", False))
        col_met2.metric("Imp. ⏳", filtrar_contar_editado("Import", False))
        col_met3.metric("Estr. ⏳", filtrar_contar_editado("Estrat", False))
        col_met4.metric("Crit. ✅", filtrar_contar_editado("Crit", True))
        col_met5.metric("Imp. ✅", filtrar_contar_editado("Import", True))
        col_met6.metric("Estr. ✅", filtrar_contar_editado("Estrat", True))

    col_btn, col_esp = st.columns([2, 8])
    with col_btn:
        btn_guardar = st.button("💾 GUARDAR CAMBIOS", use_container_width=True)

    # --- LÓGICA DE GUARDADO ---
    if btn_guardar:
        # Actualizamos el dataframe maestro con lo editado
        df.loc[df_editado.index, COL_OK] = df_editado[COL_OK]
        df_f = df.copy()
        df_f[COL_OK] = df_f[COL_OK].apply(lambda x: "OK" if x == True else "_")
        
        try:
            st.session_state.hoja.clear()
            st.session_state.hoja.update([df_f.columns.values.tolist()] + df_f.values.tolist())
            df_f.to_excel("Listado de Pendientes.xlsx", index=False)
            st.toast("Guardado en Nube y Excel ✅")
            st.session_state.df_maestro = df_f
            st.rerun()
        except Exception as e:
            st.error(f"Error al guardar: {e}")