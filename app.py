import streamlit as st
import pandas as pd
import fitz  # PyMuPDF
import re

st.set_page_config(page_title="Análisis Automático de Ofertas de Compra")
st.title("📄 Análisis Automático de Ofertas de Compra")

uploaded_files = st.file_uploader("Cargar una o más ofertas en PDF (hasta 6)", type=["pdf"], accept_multiple_files=True)

st.markdown("### 📝 O pegar texto manualmente (opcional)")
manual_text = st.text_area("Ingresar texto de una cotización:", height=300)

def extract_text_from_pdf(file):
    try:
        doc = fitz.open(stream=file.read(), filetype="pdf")
        return "\n".join([page.get_text() for page in doc])
    except Exception:
        return ""

def parse_mma_format(text):
    items = []
    for line in text.split("\n"):
        match = re.search(r'(\d{3})\s+(\S+)\s+(\d+)\s+(.*?)\s+(\d{1,3}[.,]\d{2})\s+(\d{1,3}[.,]\d{2})$', line)
        if match:
            items.append({
                "Código": match.group(2),
                "Descripción": match.group(4).strip(),
                "Cantidad": int(match.group(3)),
                "Precio Unitario (USD)": float(match.group(5).replace(",", ".")),
                "Valor Total (USD)": float(match.group(6).replace(",", ".")),
                "Proveedor": "MMA"
            })
    return items

def parse_cameron_format(text):
    items = []
    lines = text.split("\n")
    for i, line in enumerate(lines):
        if re.search(r'\d+\s+[A-Z0-9.-]+\s+\d+\s+EA\s+\d{1,3}[.,]\d{2}\s+\d{1,3}[.,]\d{2}', line):
            parts = line.split()
            try:
                codigo = parts[1]
                cantidad = int(parts[2])
                unit = float(parts[5].replace(",", ""))
                total = float(parts[6].replace(",", ""))
                descripcion = lines[i + 1].strip() if i + 1 < len(lines) else ""
                items.append({
                    "Código": codigo,
                    "Descripción": descripcion,
                    "Cantidad": cantidad,
                    "Precio Unitario (USD)": unit,
                    "Valor Total (USD)": total,
                    "Proveedor": "CAMERON"
                })
            except:
                continue
    return items

def detect_format_and_parse(text):
    if "Oferta N° 1020684" in text:
        return parse_mma_format(text)
    elif "CAMERON ARGENTINA" in text or "Document number" in text:
        return parse_cameron_format(text)
    return []

all_items = []

# Archivos PDF
for file in uploaded_files:
    raw_text = extract_text_from_pdf(file)
    parsed_items = detect_format_and_parse(raw_text)
    if parsed_items:
        all_items.extend(parsed_items)
    else:
        st.warning(f"⚠️ No se encontraron datos estructurados en el archivo: {file.name}")

# Texto pegado manualmente
if manual_text.strip():
    parsed_items = detect_format_and_parse(manual_text)
    if parsed_items:
        all_items.extend(parsed_items)
        st.success("✅ Datos extraídos del texto manual correctamente.")
    else:
        st.warning("⚠️ No se detectaron ítems válidos en el texto ingresado.")

# Mostrar resultados
if all_items:
    df = pd.DataFrame(all_items)
    st.markdown("### 📊 Comparativa Consolidada")
    st.dataframe(df, use_container_width=True)

    st.markdown("### 💰 Total por Proveedor")
    total_df = df.groupby("Proveedor")["Valor Total (USD)"].sum().reset_index()
    st.dataframe(total_df)

    mejor = total_df.loc[total_df["Valor Total (USD)"].idxmin()]
    st.success(f"🏆 **Proveedor sugerido:** {mejor['Proveedor']} (USD {mejor['Valor Total (USD)']:.2f})")
else:
    st.error("❌ No se encontraron datos útiles en los archivos cargados o texto ingresado.")

