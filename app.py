import streamlit as st
import pdfplumber
import pandas as pd
import re
from io import BytesIO
import tempfile

st.set_page_config(page_title="Comparador de Ofertas PDF", layout="wide")
st.title("📄 Comparador Automático de Ofertas en PDF")

uploaded_files = st.file_uploader("📎 Cargar una o más ofertas en PDF", type=["pdf"], accept_multiple_files=True)

def extraer_texto(pdf_path):
    texto = ""
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            if page.extract_text():
                texto += page.extract_text() + "\n"
    return texto

def extraer_items(texto):
    items = []
    patron = re.compile(r"(\d{2,6})\s+([A-Z0-9./\-]+)\s+(\d{1,3})\s+([A-ZÁÉÍÓÚÑ()\-/.,\s\d]+?)\s+(\d{1,3}(?:[.,]\d{3})*[.,]\d{2})\s+(\d{1,3}(?:[.,]\d{3})*[.,]\d{2})")
    for match in patron.findall(texto):
        codigo, ref, cantidad, descripcion, unit, total = match
        try:
            items.append({
                "Código": ref,
                "Descripción": descripcion.strip(),
                "Cantidad": int(cantidad),
                "Precio Unitario (USD)": float(unit.replace(".", "").replace(",", ".")),
                "Valor Total (USD)": float(total.replace(".", "").replace(",", "."))
            })
        except:
            continue
    return items

def buscar_condicion(texto, clave):
    patrones = {
        "forma_pago": r"(forma de pago|pago:?)\s*:?\s*(.+?)(\n|$)",
        "plazo_entrega": r"(plazo de entrega|entrega:?)\s*:?\s*(.+?)(\n|$)",
        "incoterm": r"(incoterm|entrega en|transporte:?)\s*:?\s*(.+?)(\n|$)"
    }
    if clave in patrones:
        match = re.search(patrones[clave], texto, re.IGNORECASE)
        if match:
            return match.group(2).strip()
    return ""

datos = []

if uploaded_files:
    for archivo in uploaded_files:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(archivo.read())
            texto = extraer_texto(tmp.name)

        proveedor = archivo.name.replace(".pdf", "")
        items = extraer_items(texto)
        if items:
            for item in items:
                item["Proveedor"] = proveedor
                item["Plazo Entrega"] = buscar_condicion(texto, "plazo_entrega")
                item["Forma de Pago"] = buscar_condicion(texto, "forma_pago")
                item["Incoterm"] = buscar_condicion(texto, "incoterm")
            datos.extend(items)
        else:
            st.warning(f"⚠️ No se detectaron ítems válidos en: {archivo.name}")

if datos:
    df = pd.DataFrame(datos)
    st.subheader("📊 Comparativa de Ofertas")
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
    st.info("📂 Cargá uno o más PDFs para iniciar la comparativa.")
