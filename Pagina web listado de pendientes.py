import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd

st.set_page_config(layout="wide")
st.title("Prueba de Conexión Local - Curtiembre")

def conectar():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    # Usamos el archivo físico que tenés en la carpeta
    creds = ServiceAccountCredentials.from_json_keyfile_name("creed.json", scope)
    client = gspread.authorize(creds)
    return client.open("pendientes").sheet1

try:
    hoja = conectar()
    datos = hoja.get_all_records()
    df = pd.DataFrame(datos)
    st.success("¡Conectado con éxito!")
    st.dataframe(df)
except Exception as e:
    st.error(f"Error al conectar: {e}")