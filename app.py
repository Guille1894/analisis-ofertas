import streamlit as st
import pdfplumber
import pandas as pd
import re
import tempfile
from io import BytesIO

st.set_page_config(page_title="Comparador de Ofertas PDF", layout="wide")
st.title("📄 Comparador Automático de Ofertas en PDF")

st.markdown("Subí una o varias ofertas en PDF. La app extraerá los ítems, los comparará y recomendará el mejor proveedor.")

uploaded_files = st.file_uploader("Cargar PDFs", type=["pdf"], accept_multiple_files=True)

def extraer_texto(pdf_file):
    text = ""
    with pdfplumber.open(pdf_file) as pdf:
        for page in pdf.pages:
            text += page.extract_text() + "\n"
    return text

def parsear_items(texto):
    patrones = re.findall(r"(\d{3,5})\s+([A-Z0-9./\-]+)\s+(\d+)\s+([A-ZÁÉÍÓÚÑ()\-/,.;°\s\d]+?)\s+(\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2}))\s+(\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2}))", texto)
    items = []
    for p in patrones:
        items.append({
            "Código": p[1],
            "Descripción": p[3].strip(),
            "Cantidad": int(p[2]),
            "Precio Unitario (USD)": float(p[4].replace(".", "").replace(",", ".")),
            "Valor Total (USD)": float(p[5].replace(".", "").replace(",", "."))
        })
    return items

def buscar_condicion(texto, clave):
    patrones = {
        "forma_pago": r"(forma de pago|pago:?)\s*:?\s*(.+?)(\n|$)",
        "plazo_entrega": r"(plazo de entrega|entrega:?)\s*:?\s*(.+?)(\n|$)",
        "incoterm": r"(incoterm|lugar de entrega|transporte:?)\s*:?\s*(.+?)(\n|$)"
    }
    if clave in patrones:
        match = re.search(patrones[clave], texto, re.IGNORECASE)
        if match:
            return match.group(2).strip()
    return ""

todos = []

if uploaded_files:
    for archivo in uploaded_files:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(archivo.read())
            texto = extraer_texto(tmp.name)

        proveedor = archivo.name.replace(".pdf", "")
        items = parsear_items(texto)
        if items:
            for item in items:
                item["Proveedor"] = proveedor
                item["Plazo Entrega"] = buscar_condicion(texto, "plazo_entrega")
                item["Forma de Pago"] = buscar_condicion(texto, "forma_pago")
                item["Incoterm"] = buscar_condicion(texto, "incoterm")
            todos.extend(items)
        else:
            st.warning(f"No se detectaron ítems válidos en: {archivo.name}")

if todos:
    df = pd.DataFrame(todos)
    st.subheader("📊 Comparativa Consolidada")
    st.dataframe(df, use_container_width=True)

    resumen = df.groupby("Proveedor")["Valor Total (USD)"].sum().reset_index()
    resumen = resumen.sort_values("Valor Total (USD)")
    mejor = resumen.iloc[0]

    st.subheader("💰 Total por Proveedor")
    st.dataframe(resumen)

    st.success(f"🏆 Proveedor recomendado: {mejor['Proveedor']} (USD {mejor['Valor Total (USD)']:.2f})")

    output = BytesIO()
    df.to_excel(output, index=False)
    output.seek(0)
    st.download_button("📥 Descargar Excel comparativo", output, file_name="comparativa_ofertas.xlsx")
else:
    st.info("Subí uno o más archivos PDF para iniciar la comparativa.")
