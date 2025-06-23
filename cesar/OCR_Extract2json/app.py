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
st.title("📑 Analyseur de Relevés Bancaires")

# ------------------- DOSSIERS -------------------
TEMP_DIR = "data/tmp_streamlit"
IMAGE_DIR = os.path.join(TEMP_DIR, "pdf_pages")
PREPROCESS_JSON_PATH = os.path.join(TEMP_DIR, "preprocess_config.json")
OCR_OUTPUT_DIR = "data/ocr"
ANNOTATED_DIR = "data/ocr_visualization"
os.makedirs(TEMP_DIR, exist_ok=True)
os.makedirs(IMAGE_DIR, exist_ok=True)
os.makedirs(OCR_OUTPUT_DIR, exist_ok=True)

# ------------------- UTILS -------------------
def convertir_pdf_en_images(pdf_path, prefix):
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

def construire_config_preprocessing():
    st.markdown("### ⚙️ Paramètres de preprocessing")
    config = {}

    impairs_1_15 = [i for i in range(1, 16, 2)]
    impairs_1_20 = [i for i in range(1, 21, 2)]

    config["deskew"] = {
        "enabled": st.checkbox("Deskew", value=True),
        "confidence_threshold": st.slider("Seuil de confiance (deskew)", 0, 5, 2)
    }

    config["blur"] = {
        "enabled": st.checkbox("Flou", value=True),
        "kernel_size": st.select_slider("Taille noyau (blur)", options=impairs_1_15, value=3)
    }

    config["background_cleaning"] = {
        "enabled": st.checkbox("Nettoyage du fond (tout pixel donc plus de x% du voisinnage est de la même teinte est mis à blanc):", value=True),
        "taille_voisinage": st.select_slider("Voisinage", options=impairs_1_20, value=5),
        "tol": st.slider("Tolérance", 0, 50, 15),
        "pourcentage_similaire": st.slider("% similaire", 0.0, 1.0, 0.35)
    }

    config["clahe"] = {
        "enabled": st.checkbox("CLAHE (amélioration contraste)", value=False)
    }

    config["binarization"] = {
        "enabled": st.checkbox("Binarisation : convertit le pdf en niveaux de gris", value=True),
        "block_size": st.select_slider("Taille de bloc", options=impairs_1_15, value=5),
        "C": st.slider("Constante C", -1, 5, 2)
    }

    return config


# ------------------- UI -------------------
col_gauche, col_centre, col_droite = st.columns([0.2, 1.5, 1.5])

with col_centre:
    st.markdown("### 📤 Charger un PDF")
    uploaded_pdf = st.file_uploader("Déposez un fichier PDF", type=["pdf"])

    if uploaded_pdf:
        nom_base = Path(uploaded_pdf.name).stem
        pdf_path = os.path.join(TEMP_DIR, f"{nom_base}.pdf")
        with open(pdf_path, "wb") as f:
            f.write(uploaded_pdf.read())
        st.session_state["pdf_path"] = pdf_path

        # Affichage immédiat du PDF brut
        brut_images = convertir_pdf_en_images(pdf_path, nom_base)
        st.session_state["brut_images"] = brut_images

        # Choix du mode juste après upload PDF
        mode = st.radio("🧭 Choisir le mode de traitement :", ["Analyse OCR", "Preprocessing"], horizontal=True)
        st.session_state["current_mode"] = mode

        if mode == "Analyse OCR":
            config_dir = "configs"
            available_configs = [f for f in os.listdir(config_dir) if f.endswith(".yaml")]
            selected_config = st.selectbox("⚙️ Choisir un fichier de configuration", available_configs)

            if st.button("🚀 Lancer l'analyse OCR"):
                output_json = os.path.join(TEMP_DIR, f"{nom_base}_output.json")
                vis_path = f"{ANNOTATED_DIR}/{nom_base}_annotated.pdf"

                try:
                    subprocess.run([
                        "python3", "parsers/extract_data.py",
                        "--pdf", pdf_path,
                        "--config", os.path.join(config_dir, selected_config),
                        "--output", output_json
                    ], check=True)

                    with open(output_json, "r", encoding="utf-8") as f:
                        st.session_state["json_output"] = json.load(f)

                    if os.path.exists(vis_path):
                        st.session_state["annot_images"] = convertir_pdf_en_images(vis_path, nom_base + "_annot")

                except subprocess.CalledProcessError as e:
                    st.error("Erreur pendant l'exécution du parsing OCR")
                    st.text(str(e))

            # ✅ Affichage du JSON en dehors du bouton, persistant entre reruns
            if "json_output" in st.session_state:
                with st.expander("📦 Résultat JSON structuré", expanded=True):
                    st.json(st.session_state["json_output"])



        elif mode == "Preprocessing":
            st.markdown("### 🧪 Paramètres OCR")
            col1, col2 = st.columns(2)
            with col1:
                psm_options = {
                    0: "0 – Orientation automatique + mise en page automatique",
                    1: "1 – Orientation automatique + analyse de mise en page, sans OCR",
                    2: "2 – OCR seulement, sans mise en page",
                    3: "3 – OCR complet : orientation + mise en page",
                    4: "4 – Une seule colonne de texte de taille variable",
                    5: "5 – Texte aligné verticalement (colonne unique alignée à gauche)",
                    6: "6 – Bloc uniforme de texte (mode par défaut recommandé)",
                    7: "7 – Traitement d’une seule ligne de texte",
                    8: "8 – Traitement d’un mot unique",
                    9: "9 – Mot unique dans un cercle (chèque, captcha...)",
                    10: "10 – Un seul caractère",
                    11: "11 – Ligne de texte clairsemée",
                    12: "12 – Texte clairsemé (OCR sur texte dispersé, pas en lignes)",
                    13: "13 – RAW line – Ligne brute sans heuristique"
                }

                psm_display = list(psm_options.values())
                psm_selected_label = st.selectbox("PSM (Page Segmentation Mode)", psm_display, index=6)  # 6 = mode standard
                psm = [k for k, v in psm_options.items() if v == psm_selected_label][0]

            with col2:
                oem_options = {
                    0: "0 – Legacy engine only",
                    1: "1 – Neural nets LSTM only",
                    2: "2 – Legacy + LSTM",
                    3: "3 – Default engine"
                }
                oem_display = list(oem_options.values())
                oem_selected_label = st.selectbox("OEM (OCR Engine Mode)", oem_display, index=3)
                oem = [k for k, v in oem_options.items() if v == oem_selected_label][0]
            no_preprocess = st.checkbox("Désactiver le preprocessing", value=False)

            if not no_preprocess:
                preprocessing_config = construire_config_preprocessing()
            else:
                preprocessing_config = None

            if st.button("🚀 Lancer le preprocessing"):
                if preprocessing_config:
                    with open(PREPROCESS_JSON_PATH, "w", encoding="utf-8") as f:
                        json.dump(preprocessing_config, f, indent=2)

                try:
                    cmd = [
                        "python3", "parsers/ocr_reader.py",
                        pdf_path,
                        "--output-dir", OCR_OUTPUT_DIR,
                        "--psm", str(psm),
                        "--oem", str(oem)
                    ]
                    if no_preprocess:
                        cmd.append("--no-preprocess")
                    else:
                        cmd += ["--with-preprocessing-config", PREPROCESS_JSON_PATH]

                    subprocess.run(cmd, check=True)

                    json_output_path = os.path.join(OCR_OUTPUT_DIR, f"{nom_base}.json")

                    pdf_annotated = os.path.join(ANNOTATED_DIR, f"{nom_base}_annotated.pdf")
                    if os.path.exists(pdf_annotated):
                        st.session_state["annot_images"] = convertir_pdf_en_images(pdf_annotated, nom_base + "_annot")

                except subprocess.CalledProcessError as e:
                    st.error("❌ Erreur lors du preprocessing")
                    st.text(str(e))
                                
                

    
with col_droite:
    if "brut_images" in st.session_state:
        afficher_pdf_par_image(st.session_state["brut_images"], "📄 PDF brut", "brut")

    if "annot_images" in st.session_state:
        afficher_pdf_par_image(st.session_state["annot_images"], "🖍️ PDF OCR annoté", "annot")