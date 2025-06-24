import streamlit as st
import pdfplumber
import re
import pandas as pd
from io import BytesIO

st.set_page_config(page_title="Análisis de Ofertas de Compra", layout="wide")
st.title("📄 Análisis Automático de Ofertas de Compra")

uploaded_file = st.file_uploader("Cargar oferta en PDF", type=["pdf"])

@st.cache_data
def extract_pdf_text(file):
    with pdfplumber.open(file) as pdf:
        text = "\n".join(page.extract_text() for page in pdf.pages if page.extract_text())
    return text

@st.cache_data
def extract_table_axens(text):
    pattern = r"(?P<code>\w+)\s+(?P<description>.+?)\s+(?P<hs>\d{10})\s+(?P<qty>[\d.,]+)\s+KG\s+\$(?P<unit_price>[\d.,]+)\s+\$(?P<net_value>[\d.,]+)"
    matches = re.findall(pattern, text)
    data = [
        {
            "Código": m[0],
            "Descripción": m[1],
            "HS Code": m[2],
            "Cantidad (KG)": float(m[3].replace(",", "")),
            "Precio Unitario (USD)": float(m[4].replace(",", "")),
            "Valor Total (USD)": float(m[5].replace(",", "")),
            "Proveedor": "Axens"
        } for m in matches
    ]
    return pd.DataFrame(data)

@st.cache_data
def extract_table_topsoe(text):
    pattern = r"(TK-\d+.*?)\s+(\d+[.,]?\d*)\s+KG\s+USD\s+(\d+[.,]?\d*)\s+USD\s+(\d+[.,]?\d*)"
    matches = re.findall(pattern, text)
    data = [
        {
            "Código": m[0].split()[0],
            "Descripción": m[0],
            "Cantidad (KG)": float(m[1].replace(",", "")),
            "Precio Unitario (USD)": float(m[2].replace(",", "")),
            "Valor Total (USD)": float(m[3].replace(",", "")),
            "Proveedor": "Topsoe"
        } for m in matches
    ]
    return pd.DataFrame(data)

if uploaded_file:
    pdf_text = extract_pdf_text(uploaded_file)

    if "Axens" in pdf_text:
        df = extract_table_axens(pdf_text)
    elif "Topsoe" in pdf_text:
        df = extract_table_topsoe(pdf_text)
    else:
        st.warning("No se pudo identificar el proveedor automáticamente.")
        df = pd.DataFrame()

    if not df.empty:
        st.success("Datos extraídos correctamente")
        st.dataframe(df, use_container_width=True)

        total = df.groupby("Proveedor")["Valor Total (USD)"].sum().reset_index()
        st.subheader("💰 Total por Proveedor")
        st.table(total)

        st.download_button(
            label="📥 Descargar Excel con análisis",
            data=df.to_excel(index=False, engine='openpyxl'),
            file_name="analisis_oferta.xlsx"
        )
    else:
        st.error("No se encontraron datos estructurados en el PDF cargado.")
