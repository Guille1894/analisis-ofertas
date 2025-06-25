import streamlit as st
import pandas as pd
import fitz  # PyMuPDF
import re
from io import BytesIO

st.set_page_config(page_title="Análisis Automático de Ofertas de Compra")

st.title("📄 Análisis Automático de Ofertas de Compra")
st.markdown("Cargar una o más ofertas en PDF (hasta 6)")

uploaded_files = st.file_uploader(" ", type=["pdf"], accept_multiple_files=True)

# NUEVO: opción para ingresar texto manualmente
st.markdown("### 📝 O pegar texto de una oferta manualmente (opcional)")
manual_text = st.text_area("Ingresar texto de una cotización:", height=300)

def extract_text_from_pdf(file):
    try:
        doc = fitz.open(stream=file.read(), filetype="pdf")
        text = "\n".join([page.get_text() for page in doc])
        return text
    except Exception as e:
        return ""

def parse_offer_text(text):
    items = []
    proveedor = ""
    plazo = ""
    forma_pago = ""
    incoterm = ""

    # Detectar proveedor desde encabezado
    proveedor_match = re.search(r'(?:Proveedor|PROVEEDOR|Proveedor:)\s*[:\-]?\s*(.+)', text)
    if proveedor_match:
        proveedor = proveedor_match.group(1).strip().split("\n")[0]

    # Detectar condiciones comerciales
    if "forma de pago" in text.lower():
        forma_pago_match = re.search(r'forma de pago[:\-]?\s*(.+)', text, re.IGNORECASE)
        if forma_pago_match:
            forma_pago = forma_pago_match.group(1).strip().split("\n")[0]
    if "plazo de entrega" in text.lower():
        plazo_match = re.search(r'plazo de entrega[:\-]?\s*(.+)', text, re.IGNORECASE)
        if plazo_match:
            plazo = plazo_match.group(1).strip().split("\n")[0]
    if "incoterm" in text.lower():
        incoterm_match = re.search(r'incoterm[:\-]?\s*(.+)', text, re.IGNORECASE)
        if incoterm_match:
            incoterm = incoterm_match.group(1).strip().split("\n")[0]

    # Detectar líneas de ítems con precios
    for match in re.finditer(r'(?P<codigo>\d{4,})[^\n]*?(?P<desc>[A-Z \-\,0-9\(\)/]+)\s+(?P<cant>\d+)\s+(?P<unit>\d{2,}[,.]?\d*)\s+(?P<total>\d{2,}[,.]?\d*)', text):
        items.append({
            "Código": match.group("codigo"),
            "Descripción": match.group("desc").strip(),
            "Cantidad": int(match.group("cant")),
            "Precio Unitario (USD)": float(match.group("unit").replace(",", "")),
            "Valor Total (USD)": float(match.group("total").replace(",", "")),
            "Proveedor": proveedor,
            "Incoterm": incoterm,
            "Plazo": plazo,
            "Forma de Pago": forma_pago
        })

    return items

all_data = []

# Procesar PDFs
for file in uploaded_files:
    raw_text = extract_text_from_pdf(file)
    items = parse_offer_text(raw_text)
    if items:
        all_data.extend(items)
    else:
        st.warning(f"⚠️ No se encontraron datos estructurados en el archivo: {file.name}")

# Procesar texto manual
if manual_text.strip():
    manual_items = parse_offer_text(manual_text)
    if manual_items:
        all_data.extend(manual_items)
        st.success("✅ Datos extraídos del texto manual correctamente.")
    else:
        st.warning("⚠️ No se detectaron ítems válidos en el texto ingresado.")

if all_data:
    df = pd.DataFrame(all_data)

    st.markdown("### 📊 Comparativa Consolidada")
    st.dataframe(df, use_container_width=True)

    st.markdown("### 💰 Total por Proveedor")
    total_df = df.groupby("Proveedor")["Valor Total (USD)"].sum().reset_index()
    st.dataframe(total_df)

    # Proveedor sugerido (mínimo total)
    mejor = total_df.loc[total_df["Valor Total (USD)"].idxmin()]
    st.success(f"🏆 **Proveedor sugerido:** {mejor['Proveedor']} (USD {mejor['Valor Total (USD)']:.2f})")
else:
    st.error("❌ No se encontraron datos útiles en los archivos cargados o texto ingresado.")
