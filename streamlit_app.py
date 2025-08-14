# GUIADOR.py
import streamlit as st
import pandas as pd
import unicodedata
import os
from fpdf import FPDF
from datetime import datetime
from io import BytesIO

# -----------------------
# Configuración Streamlit
# -----------------------
st.set_page_config(page_title="GUIADOR IDMJI", page_icon="🎵", layout="centered")
st.markdown("<p style='text-align:center; font-size:8px;'>By Ing. Rodolfo Ibarra Machuca cel: 3045916809</p>", unsafe_allow_html=True)

# -----------------------
# Util: normalizar texto (quitar tildes / espacios)
# -----------------------
def strip_accents(s: str) -> str:
    if not isinstance(s, str):
        return s
    s = s.strip()
    s = ''.join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")
    return s

def normalize_cols(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [strip_accents(str(c)).lower().strip() for c in df.columns]
    return df

# -----------------------
# Detectar columnas numero/titulo
# -----------------------
def find_column_for_number(df: pd.DataFrame):
    cands = ["numero", "n", "no", "num", "id", "codigo"]
    for cand in cands:
        if cand in df.columns:
            return cand
    for c in df.columns:
        try:
            s = pd.to_numeric(df[c], errors="coerce")
            if s.notna().sum() >= max(1, int(0.3 * len(df))):
                return c
        except Exception:
            continue
    return df.columns[0] if len(df.columns) > 0 else None

def find_column_for_title(df: pd.DataFrame, avoid_col=None):
    candidates = ["titulo", "nombre", "title", "cancion", "himno", "coro"]
    for cand in candidates:
        if cand in df.columns and cand != avoid_col:
            return cand
    for c in df.columns:
        if c != avoid_col and df[c].dtype == object:
            return c
    return df.columns[0] if len(df.columns) > 0 else None

# -----------------------
# Cargar tablas HIMNOS.xlsx y COROS.xlsx
# -----------------------
HIMNOS_FILE = "HIMNOS.xlsx"
COROS_FILE = "COROS.xlsx"

def load_table(path):
    if not os.path.exists(path):
        return None, f"No se encontró el archivo '{path}'. Coloca '{path}' junto al script."
    try:
        df = pd.read_excel(path, engine="openpyxl")
    except Exception as e:
        return None, f"Error leyendo '{path}': {e}"
    if df is None or df.empty:
        return None, f"'{path}' está vacío o no tiene filas."
    df = normalize_cols(df)
    return df, None

himnos_df, err_h = load_table(HIMNOS_FILE)
coros_df, err_c = load_table(COROS_FILE)

if err_h or err_c:
    st.title("GUIADOR - Error al cargar datos")
    if err_h:
        st.error(err_h)
    if err_c:
        st.error(err_c)
    st.stop()

# Detectar columnas
him_num_col = find_column_for_number(himnos_df)
him_tit_col = find_column_for_title(himnos_df, avoid_col=him_num_col)
coro_num_col = find_column_for_number(coros_df)
coro_tit_col = find_column_for_title(coros_df, avoid_col=coro_num_col)

# Convertir columna número a str
himnos_df[him_num_col] = himnos_df[him_num_col].astype(str).str.strip()
coros_df[coro_num_col] = coros_df[coro_num_col].astype(str).str.strip()

# -----------------------
# Estilos simples
# -----------------------
st.markdown(
    """
    <style>
    .center-title {text-align:center; color:#0b3d91; font-weight:700; margin-bottom:6px;}
    .form-box {background: rgba(255,255,255,0.98); padding:14px; border-radius:10px; box-shadow: 0 6px 18px rgba(0,0,0,0.06);}
    </style>
    """,
    unsafe_allow_html=True
)

# -----------------------
# Session state inicial
# -----------------------
if "fase" not in st.session_state:
    st.session_state.fase = 1
if "config" not in st.session_state:
    st.session_state.config = {"himnos": 0, "coros": 0, "coro_diezmo": False, "coro_final": False}

# -----------------------
# FASE 1 - Configuración
# -----------------------
if st.session_state.fase == 1:
    col_logo, col_title = st.columns([2, 4])
    with col_logo:
        if os.path.exists("logo.png"):
            st.image("logo.png", width=180)
    with col_title:
        st.markdown("<h1 style='margin-bottom:0;'>GUIADOR IDMJI</h1>", unsafe_allow_html=True)
        
    st.markdown("<div class='form-box'>", unsafe_allow_html=True)
    st.subheader("📋 Configuración")
    
    c1, c2 = st.columns(2)
    with c1:
        usar_h = st.checkbox("¿Incluir Himnos?", value=True)
        if usar_h:
            num_h = st.number_input("¿Cuántos himnos?", min_value=1, max_value=10, value=4, step=1)
        else:
            num_h = 0
        usar_diezmo = st.checkbox("¿Incluir Coro de Diezmo?", value=False)
    with c2:
        usar_c = st.checkbox("¿Incluir Coros?", value=True)
        if usar_c:
            num_c = st.number_input("¿Cuántos coros?", min_value=1, max_value=10, value=2, step=1)
        else:
            num_c = 0
        usar_final = st.checkbox("¿Incluir Coro Final?", value=False)

    st.write("Cuando esté listo presiona Continuar.")
    if st.button("➡️ Continuar", use_container_width=True):
        st.session_state.config["himnos"] = int(num_h)
        st.session_state.config["coros"] = int(num_c)
        st.session_state.config["coro_diezmo"] = bool(usar_diezmo)
        st.session_state.config["coro_final"] = bool(usar_final)
        st.session_state.fase = 2
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

# -----------------------
# FASE 2 - Formulario dinámico y Generar PDF/TXT
# -----------------------
elif st.session_state.fase == 2:
    col_logo, col_title = st.columns([2, 4])
    with col_logo:
        if os.path.exists("logo.png"):
            st.image("logo.png", width=180)
    with col_title:
        st.markdown("<h1 style='margin-bottom:0;'>GUIADOR IDMJI</h1>", unsafe_allow_html=True)
        
    st.markdown('<div class="form-box">', unsafe_allow_html=True)
    st.subheader("✍️ Información del servicio")

    # --- HIMNOS ---
    himnos_lista = []
    if st.session_state.config.get("himnos", 0) > 0:
        st.markdown("### 🎵 Himnos")
        for i in range(st.session_state.config["himnos"]):
            col_num, col_title = st.columns([1, 6])
            key = f"him_num_{i}"
            with col_num:
                st.number_input("", min_value=1, max_value=999, step=1, key=key)
            with col_title:
                search = str(st.session_state.get(key, "")).strip()
                title = ""
                if search != "":
                    match = himnos_df.loc[himnos_df[him_num_col].astype(str).str.strip() == search, him_tit_col]
                    if not match.empty:
                        title_raw = match.iloc[0]
                        title = strip_accents(str(title_raw))
                if search != "":
                    himnos_lista.append((search, title))
                st.markdown(f"{title if title else '— número no encontrado —'}")

    # --- COROS ---
    coros_lista = []
    if st.session_state.config.get("coros", 0) > 0:
        st.markdown("### 🎶 Coros")
        for i in range(st.session_state.config["coros"]):
            col_num, col_title = st.columns([1, 6])
            key = f"coro_num_{i}"
            with col_num:
                st.number_input("", min_value=1, max_value=999, step=1, key=key)
            with col_title:
                search = str(st.session_state.get(key, "")).strip()
                title = ""
                if search != "":
                    match = coros_df.loc[coros_df[coro_num_col].astype(str).str.strip() == search, coro_tit_col]
                    if not match.empty:
                        title_raw = match.iloc[0]
                        title = strip_accents(str(title_raw))
                if search != "":
                    coros_lista.append((search, title))
                st.markdown(f"{title if title else '— número no encontrado —'}")

    # --- CORO DIEZMO ---
    coro_diezmo = ""
    num_diezmo = ""
    if st.session_state.config.get("coro_diezmo", False):
        st.markdown("### 💰 Coro de Diezmo")
        col_num, col_title = st.columns([1, 6])
        key_d = "num_diezmo"
        with col_num:
            st.number_input("", min_value=1, max_value=999, step=1, key=key_d)
        with col_title:
            search = str(st.session_state.get(key_d, "")).strip()
            if search != "":
                match = coros_df.loc[coros_df[coro_num_col].astype(str).str.strip() == search, coro_tit_col]
                if not match.empty:
                    coro_diezmo = strip_accents(str(match.iloc[0]))
                    num_diezmo = search
            st.markdown(f"{coro_diezmo if coro_diezmo else '— número no encontrado —'}")

    # --- CORO FINAL ---
    coro_final = ""
    num_final = ""
    if st.session_state.config.get("coro_final", False):
        st.markdown("### 🏁 Coro Final")
        col_num, col_title = st.columns([1, 6])
        key_f = "num_final"
        with col_num:
            st.number_input("", min_value=1, max_value=999, step=1, key=key_f)
        with col_title:
            search = str(st.session_state.get(key_f, "")).strip()
            if search != "":
                match = coros_df.loc[coros_df[coro_num_col].astype(str).str.strip() == search, coro_tit_col]
                if not match.empty:
                    coro_final = strip_accents(str(match.iloc[0]))
                    num_final = search
            st.markdown(f"{coro_final if coro_final else '— número no encontrado —'}")

    # --- PREDICADOR ---
    predicador = st.text_input("Nombre del predicador", value=st.session_state.get("predicador", ""))

    # --- NOTAS ---
    notas = st.text_area("📝 Notas para el guiador/predicador", value=st.session_state.get("notas", ""), height=120)

    # Guardar en session_state
    st.session_state["predicador"] = predicador
    st.session_state["notas"] = notas

    st.markdown('</div>', unsafe_allow_html=True)

    # -----------------------
    # Funciones para PDF
    # -----------------------
    def clean_text_for_pdf(text):
        if not text:
            return ""
        return str(text).replace('\r', '')

    def create_pdf_bytes(predicador, himnos_tuples, coros_tuples, coro_diezmo_num, coro_diezmo_tit, coro_final_num, coro_final_tit, notas):
        pdf = FPDF(orientation='P', unit='mm', format='A4')
        pdf.set_left_margin(35)
        pdf.set_right_margin(15)
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.add_page()

        pdf.add_font('DejaVu', '', 'DejaVuSans.ttf', uni=True)
        pdf.add_font('DejaVu', 'B', 'DejaVuSans.ttf', uni=True)

        pdf.set_font("DejaVu", 'B', 18)
        if os.path.exists("logo.png"):
            pdf.image("logo.png", x=35, y=12, w=35)
        pdf.set_xy(0, 12)
        pdf.cell(0, 10, clean_text_for_pdf("GUIADOR IDMJI"), ln=True, align='C')

        pdf.set_font("DejaVu", '', 10)
        pdf.cell(0, 6, clean_text_for_pdf(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"), ln=True, align='C')
        pdf.ln(4)

        # --- HIMNOS ---
        if himnos_tuples:
            pdf.set_font("DejaVu", 'B', 12)
            pdf.cell(0, 8, clean_text_for_pdf("HIMNOS:"), ln=True)
            pdf.set_font("DejaVu", '', 11)
            for num, tit in himnos_tuples:
                if num.strip() != "" and tit.strip() != "":
                    if pdf.get_y() > 260:
                        pdf.add_page()
                    line = f"{clean_text_for_pdf(str(num))}  {clean_text_for_pdf(tit)}"
                    pdf.multi_cell(0, 6, line)
                    pdf.ln(1)

        # --- COROS ---
        if coros_tuples:
            pdf.ln(2)
            pdf.set_font("DejaVu", 'B', 12)
            pdf.cell(0, 8, clean_text_for_pdf("COROS:"), ln=True)
            pdf.set_font("DejaVu", '', 11)
            for num, tit in coros_tuples:
                if num.strip() != "" and tit.strip() != "":
                    if pdf.get_y() > 260:
                        pdf.add_page()
                    line = f"{clean_text_for_pdf(str(num))}  {clean_text_for_pdf(tit)}"
                    pdf.multi_cell(0, 6, line)
                    pdf.ln(1)

        # --- CORO DIEZMO ---
        if coro_diezmo_num and coro_diezmo_tit:
            pdf.ln(4)
            pdf.set_font("DejaVu", 'B', 11)
            pdf.cell(0, 6, clean_text_for_pdf("CORO DIEZMO:"), ln=1)
            pdf.set_font("DejaVu", '', 11)
            line = f"{clean_text_for_pdf(str(coro_diezmo_num))}  {clean_text_for_pdf(coro_diezmo_tit)}"
            pdf.multi_cell(0, 6, line)

        # --- CORO FINAL ---
        if coro_final_num and coro_final_tit:
            pdf.ln(4)
            pdf.set_font("DejaVu", 'B', 11)
            pdf.cell(0, 6, clean_text_for_pdf("CORO FINAL:"), ln=1)
            pdf.set_font("DejaVu", '', 11)
            line = f"{clean_text_for_pdf(str(coro_final_num))}  {clean_text_for_pdf(coro_final_tit)}"
            pdf.multi_cell(0, 6, line)

        # --- PREDICADOR ---
        pdf.ln(4)
        pdf.set_font("DejaVu", 'B', 11)
        pdf.cell(0, 6, clean_text_for_pdf("PREDICADOR:"), ln=1)
        pdf.set_font("DejaVu", '', 11)
        pdf.multi_cell(0, 6, clean_text_for_pdf(predicador))

        # --- NOTAS ---
        pdf.ln(4)
        pdf.set_font("DejaVu", 'B', 11)
        pdf.cell(0, 6, clean_text_for_pdf("NOTA:"), ln=1)
        x = pdf.get_x()
        y = pdf.get_y()
        h_box = 40
        pdf.rect(x, y, 145, h_box)
        pdf.set_xy(x + 2, y + 2)
        pdf.set_font("DejaVu", '', 11)
        pdf.multi_cell(0, 5, clean_text_for_pdf(notas))

        # ✅ Exportar correctamente a bytes
        pdf_bytes = pdf.output(dest='S').encode('latin1')
        return pdf_bytes

    # -----------------------
    # Botones inferiores
    # -----------------------
    col0, col1, col2 = st.columns([1,1,1])

    with col0:
        if st.button("📄 Generar PDF", use_container_width=True):
            himnos_res = [(str(st.session_state.get(f"him_num_{i}", "")).strip(), 
                           himnos_df.loc[himnos_df[him_num_col].astype(str).str.strip() == str(st.session_state.get(f"him_num_{i}", "")).strip(), him_tit_col].iloc[0] if not himnos_df.loc[himnos_df[him_num_col].astype(str).str.strip() == str(st.session_state.get(f"him_num_{i}", "")).strip(), him_tit_col].empty else "") 
                          for i in range(st.session_state.config.get("himnos",0)) if str(st.session_state.get(f"him_num_{i}", "")).strip() != ""]

            coros_res = [(str(st.session_state.get(f"coro_num_{i}", "")).strip(), 
                          coros_df.loc[coros_df[coro_num_col].astype(str).str.strip() == str(st.session_state.get(f"coro_num_{i}", "")).strip(), coro_tit_col].iloc[0] if not coros_df.loc[coros_df[coro_num_col].astype(str).str.strip() == str(st.session_state.get(f"coro_num_{i}", "")).strip(), coro_tit_col].empty else "") 
                         for i in range(st.session_state.config.get("coros",0)) if str(st.session_state.get(f"coro_num_{i}", "")).strip() != ""]

            pdf_bytes = create_pdf_bytes(
                st.session_state.get("predicador",""),
                himnos_res,
                coros_res,
                num_diezmo,
                coro_diezmo,
                num_final,
                coro_final,
                st.session_state.get("notas","")
            )
            st.download_button(
                "⬇️ Descargar PDF",
                data=pdf_bytes,
                file_name=f"GUIADOR_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                mime="application/pdf"
            )
