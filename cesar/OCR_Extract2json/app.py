import streamlit as st
import os
import subprocess
import json
from pathlib import Path
import shutil
import fitz  # PyMuPDF
from PIL import Image

# ------------------- CONFIG STREAMLIT -------------------
st.set_page_config(page_title="OCR Parser", layout="wide")
st.title("📑 Analyseur de Relevés Bancaires OCR")

# ------------------- DOSSIERS -------------------
TEMP_DIR = "data/tmp_streamlit"
IMAGE_DIR = os.path.join(TEMP_DIR, "pdf_pages")
os.makedirs(TEMP_DIR, exist_ok=True)
os.makedirs(IMAGE_DIR, exist_ok=True)


# ------------------- UTILS -------------------
def convertir_pdf_en_images(pdf_path, prefix):
    """Convertit un PDF en images PNG page par page et retourne la liste des chemins"""
    doc = fitz.open(pdf_path)
    image_paths = []

    for i, page in enumerate(doc):
        pix = page.get_pixmap(dpi=150)
        image_path = os.path.join(IMAGE_DIR, f"{prefix}_page_{i + 1}.png")
        pix.save(image_path)
        image_paths.append(image_path)

    return image_paths


def afficher_pdf_par_image(images, label, key_prefix):
    if not images:
        st.info("⛔ Aucune image à afficher.")
        return

    key_page = f"{key_prefix}_page"
    if key_page not in st.session_state:
        st.session_state[key_page] = 0
    page = st.session_state[key_page]

    num_pages = len(images)

    st.markdown(
        f"<h3 style='text-align: right'>{label} — Page {page + 1}/{num_pages}</h3>",
        unsafe_allow_html=True
    )

    col1, col2, col3 = st.columns([1, 4, 1])
    with col1:
        st.button("⬅", disabled=(page == 0), key=f"{key_prefix}_prev",
                  on_click=lambda: st.session_state.update({key_page: page - 1}))
    with col3:
        st.button("➡", disabled=(page == num_pages - 1), key=f"{key_prefix}_next",
                  on_click=lambda: st.session_state.update({key_page: page + 1}))

    st.image(images[page], use_container_width=True)



# ------------------- UI -------------------
col_centre, col_droite = st.columns([2, 1.4])

with col_centre:
    st.markdown("### 📤 Charger un PDF et lancer l’analyse")
    uploaded_pdf = st.file_uploader("Déposez un fichier PDF", type=["pdf"])

    config_dir = "configs"
    available_configs = [f for f in os.listdir(config_dir) if f.endswith(".yaml")]
    selected_config = st.selectbox("⚙️ Choisir un fichier de configuration", available_configs)

    nom_base = None
    json_output = None

    if uploaded_pdf:
        nom_base = Path(uploaded_pdf.name).stem
        pdf_path = os.path.join(TEMP_DIR, f"{nom_base}.pdf")
        with open(pdf_path, "wb") as f:
            f.write(uploaded_pdf.read())

        # Convertir en images pour affichage
        st.session_state["brut_images"] = convertir_pdf_en_images(pdf_path, f"{nom_base}_brut")
        st.session_state["pdf_path"] = pdf_path  # garde le chemin en mémoire

    if st.button("🚀 Lancer l’analyse") and uploaded_pdf and selected_config:
        with st.spinner("🔍 Analyse en cours..."):
            config_path = os.path.join(config_dir, selected_config)
            output_json = os.path.join(TEMP_DIR, f"{nom_base}_output.json")
            pdf_annot_path = f"data/ocr_visualization/{nom_base}_annotated.pdf"

            try:
                subprocess.run(
                    [
                        "python3", "parsers/extract_data.py",
                        "--pdf", st.session_state["pdf_path"],
                        "--config", config_path,
                        "--output", output_json
                    ],
                    check=True
                )

                with open(output_json, "r", encoding="utf-8") as f:
                    st.session_state["json_output"] = json.load(f)

                if os.path.exists(pdf_annot_path):
                    st.session_state["annot_images"] = convertir_pdf_en_images(
                        pdf_annot_path, f"{nom_base}_annot"
                    )
                    st.success("✅ Analyse terminée")
                else:
                    st.warning("⚠️ PDF annoté non généré.")

            except subprocess.CalledProcessError as e:
                st.error("❌ Une erreur est survenue durant le parsing.")
                st.text(str(e))
            
    if "json_output" in st.session_state:
        with st.expander("📦 Résultat JSON structuré", expanded=True):
            st.json(st.session_state["json_output"])


# ------------------- COLONNE DROITE : AFFICHAGE -------------------
with col_droite:
    if "brut_images" in st.session_state:
        afficher_pdf_par_image(st.session_state["brut_images"], "📄 PDF brut", "brut")

    if "annot_images" in st.session_state:
        afficher_pdf_par_image(st.session_state["annot_images"], "🖍️ PDF OCR annoté", "annot")
    elif uploaded_pdf:
        
        st.markdown(
            f"<h3 style='text-align: right'>🖍️ PDF OCR annoté</h3>",
            unsafe_allow_html=True
        )
        st.info("⚠️ Le PDF annoté sera affiché ici après l’analyse.")


# ------------------- JSON OUTPUT -------------------

