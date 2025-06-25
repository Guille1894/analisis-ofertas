import streamlit as st
import pdfplumber
import re
import pandas as pd
from io import BytesIO

st.set_page_config(page_title="Análisis de Ofertas de Compra", layout="wide")
st.title("📄 Análisis Automático de Ofertas de Compra")

uploaded_files = st.file_uploader("Cargar una o más ofertas en PDF (hasta 6)", type=["pdf"], accept_multiple_files=True)

@st.cache_data
def extract_pdf_text(file):
    with pdfplumber.open(file) as pdf:
        text = "\n".join(page.extract_text() for page in pdf.pages if page.extract_text())
    return text

def extract_table_generic(text, proveedor):
    pattern = r"(?P<codigo>\w{2,}-?\d{2,})[\s|:,-]+(?P<descripcion>[A-Za-z0-9\(\)\"'°% /.-]+)[\s|:,-]+(?P<cantidad>\d+[.,]?\d*)\s*KG[\s|:,-]+(?P<precio_unitario>\d+[.,]?\d*)\s*USD[\s|:,-]+(?P<valor_total>\d+[.,]?\d*)"
    matches = re.findall(pattern, text)
    condiciones = {
        "Incoterm": "", "Plazo": "", "Forma de pago": ""
    }
    for line in text.split("\n"):
        if "Incoterm" in line or "CFR" in line or "FOB" in line:
            condiciones["Incoterm"] = line.strip()
        if "días" in line.lower() or "dias" in line.lower():
            condiciones["Plazo"] = line.strip()
        if "pago" in line.lower():
            condiciones["Forma de pago"] = line.strip()
    data = [
        {
            "Código": m[0],
            "Descripción": m[1].strip(),
            "Cantidad (KG)": float(m[2].replace(",", "")),
            "Precio Unitario (USD)": float(m[3].replace(",", "")),
            "Valor Total (USD)": float(m[4].replace(",", "")),
            "Proveedor": proveedor,
            "Incoterm": condiciones["Incoterm"],
            "Plazo": condiciones["Plazo"],
            "Forma de pago": condiciones["Forma de pago"]
        } for m in matches
    ]
    return pd.DataFrame(data)

if uploaded_files:
    if len(uploaded_files) > 6:
        st.warning("⚠️ Por ahora se admiten hasta 6 archivos a la vez.")
        uploaded_files = uploaded_files[:6]

    all_data = []
    for file in uploaded_files:
        pdf_text = extract_pdf_text(file)

        st.markdown(f"**Texto extraído de:** `{file.name}`")
        with st.expander("Mostrar texto del PDF"):
            st.text(pdf_text[:3000] + ("..." if len(pdf_text) > 3000 else ""))

        proveedor = "Desconocido"
        if "Axens" in pdf_text:
            proveedor = "Axens"
        elif "Topsoe" in pdf_text:
            proveedor = "Topsoe"
        else:
            proveedor = file.name.split()[0].replace("_", " ")

        df = extract_table_generic(pdf_text, proveedor)

        if df.empty:
            st.warning(f"⚠️ No se encontraron datos estructurados en el archivo: {file.name}")
        else:
            all_data.append(df)

    if all_data:
        df_total = pd.concat(all_data, ignore_index=True)
        st.success("✅ Datos extraídos correctamente")
        st.dataframe(df_total, use_container_width=True)

        st.subheader("💰 Total por Proveedor")
        total = df_total.groupby("Proveedor")["Valor Total (USD)"].sum().reset_index()
        st.table(total)

        st.subheader("📊 Comparativa por Código")
        comparativa = df_total.pivot_table(index="Código", columns="Proveedor", values="Precio Unitario (USD)")
        st.dataframe(comparativa, use_container_width=True)

        st.subheader("🏆 Mejores Precios por Producto")
        mejores = comparativa.idxmin(axis=1).reset_index()
        mejores.columns = ["Código", "Proveedor más económico"]
        st.table(mejores)

        st.subheader("⚠️ Alertas de precios fuera de rango")
        alerta = comparativa.copy()
        for codigo in alerta.index:
            precios = alerta.loc[codigo].dropna()
            if not precios.empty:
                min_val = precios.min()
                alerta.loc[codigo] = ["⚠️ Alto" if v > min_val * 1.3 else "" for v in precios]
        st.dataframe(alerta.replace("", pd.NA).dropna(how="all"), use_container_width=True)

        st.subheader("💡 Ahorro potencial por ítem")
        ahorro = df_total.copy()
        ahorro["Min. Precio por Código"] = ahorro.groupby("Código")["Precio Unitario (USD)"].transform("min")
        ahorro["Sobreprecio"] = ahorro["Precio Unitario (USD)"] - ahorro["Min. Precio por Código"]
        ahorro["Ahorro Potencial (USD)"] = ahorro["Sobreprecio"] * ahorro["Cantidad (KG)"]
        ahorro_final = ahorro.groupby("Proveedor")["Ahorro Potencial (USD)"].sum().reset_index()
        st.dataframe(ahorro_final, use_container_width=True)

        buffer = BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            df_total.to_excel(writer, sheet_name='Datos Totales', index=False)
            total.to_excel(writer, sheet_name='Totales Proveedor', index=False)
            comparativa.to_excel(writer, sheet_name='Comparativa', index=True)
            mejores.to_excel(writer, sheet_name='Mejores Precios', index=False)
            alerta.to_excel(writer, sheet_name='Alertas Precios', index=True)
            ahorro_final.to_excel(writer, sheet_name='Ahorro Potencial', index=False)
        buffer.seek(0)

        st.download_button(
            label="📥 Descargar Excel con análisis completo",
            data=buffer,
            file_name="analisis_comparativo_ofertas.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        st.error("❌ No se encontraron datos útiles en los archivos cargados.")
import streamlit as st
import pdfplumber
import re
import pandas as pd
from io import BytesIO

st.set_page_config(page_title="Análisis de Ofertas de Compra", layout="wide")
st.title("📄 Análisis Automático de Ofertas de Compra")

uploaded_files = st.file_uploader("Cargar una o más ofertas en PDF", type=["pdf"], accept_multiple_files=True)

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

if uploaded_files:
    all_data = []
    for file in uploaded_files:
        pdf_text = extract_pdf_text(file)
        if "Axens" in pdf_text:
            df = extract_table_axens(pdf_text)
        elif "Topsoe" in pdf_text:
            df = extract_table_topsoe(pdf_text)
        else:
            st.warning(f"No se pudo identificar el proveedor en el archivo: {file.name}")
            df = pd.DataFrame()
        if not df.empty:
            all_data.append(df)

    if all_data:
        df_total = pd.concat(all_data, ignore_index=True)
        st.success("Datos extraídos correctamente")
        st.dataframe(df_total, use_container_width=True)

        st.subheader("💰 Total por Proveedor")
        total = df_total.groupby("Proveedor")["Valor Total (USD)"].sum().reset_index()
        st.table(total)

        st.subheader("📊 Comparativa por Código")
        comparativa = df_total.pivot_table(index="Código", columns="Proveedor", values="Precio Unitario (USD)")
        st.dataframe(comparativa, use_container_width=True)

        st.subheader("🏆 Mejores Precios por Producto")
        mejores = comparativa.idxmin(axis=1).reset_index()
        mejores.columns = ["Código", "Proveedor más económico"]
        st.table(mejores)

        # Reparar descarga con Excel válido
        buffer = BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            df_total.to_excel(writer, sheet_name='Datos Totales', index=False)
            total.to_excel(writer, sheet_name='Totales Proveedor', index=False)
            comparativa.to_excel(writer, sheet_name='Comparativa', index=True)
            mejores.to_excel(writer, sheet_name='Mejores Precios', index=False)
        buffer.seek(0)

        st.download_button(
            label="📥 Descargar Excel con análisis completo",
            data=buffer,
            file_name="analisis_comparativo_ofertas.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        st.error("No se encontraron datos estructurados en los archivos cargados.")

