import cv2
import numpy as np
from pdf2image import convert_from_path
from pytesseract import image_to_osd, Output
from PIL import Image
import os
import json

def deskew(image, config=None):
    import tempfile
    import subprocess
    import re
    import os

    confidence_threshold = 3.0
    if isinstance(config, dict):
        confidence_threshold = config.get("confidence_threshold", 3.0)

    try:
        # 📁 Tempfile image
        os.makedirs("data/tmp_osd", exist_ok=True)
        tmp_img_path = os.path.join("data/tmp_osd", "deskew_input.png")
        pil_img = Image.fromarray(image)
        pil_img.save(tmp_img_path, dpi=(300, 300))

        # 🧠 Tesseract OSD via CLI
        result = subprocess.run(
            ["tesseract", tmp_img_path, "stdout", "--psm", "0", "-l", "osd"],
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            raise RuntimeError(f"Tesseract OSD CLI error: {result.stderr}")

        osd_output = result.stdout
        angle_match = re.search(r"Rotate: (\d+)", osd_output)
        conf_match = re.search(r"Orientation confidence: ([0-9.]+)", osd_output)

        if not angle_match or not conf_match:
            raise ValueError("OSD output parsing failed.")

        angle = float(angle_match.group(1))
        confidence = float(conf_match.group(1))

        if confidence < confidence_threshold:
            print(f"[⚠️] Confiance trop faible pour corriger l'inclinaison : {confidence:.2f}")
            return image

        if angle == 0:
            print(f"[ℹ️] Aucune rotation nécessaire (angle détecté : 0°)")
            return image

        (h, w) = image.shape[:2]
        center = (w // 2, h // 2)
        rot_mat = cv2.getRotationMatrix2D(center, -angle, 1.0)
        rotated = cv2.warpAffine(image, rot_mat, (w, h), flags=cv2.INTER_LINEAR)
        print(f"[↪] Rotation appliquée : {-angle}° (confiance : {confidence:.2f})")
        return rotated

    except Exception as e:
        print(f"[❌] Deskew failed: {e}")
        return image


def remove_uniform_background_by_similarity(gray, taille_voisinage, tol, pourcentage_similaire):
    h, w = gray.shape
    result = gray.copy()

    mean_local = cv2.blur(gray.astype(np.float32), (taille_voisinage, taille_voisinage))
    diff = np.abs(gray.astype(np.float32) - mean_local)
    similar_mask = (diff <= tol).astype(np.uint8)

    kernel = np.ones((taille_voisinage, taille_voisinage), dtype=np.uint8)
    voisins_similaires = cv2.filter2D(similar_mask, -1, kernel)

    max_voisins = taille_voisinage * taille_voisinage
    seuil_voisins = int(pourcentage_similaire * max_voisins)

    masque_a_blanchir = voisins_similaires >= seuil_voisins
    result[masque_a_blanchir] = 255

    return result.astype(np.uint8)

def preprocess_page(pil_img, params=None):
    if params is None:
        params = {}

    img = np.array(pil_img)
    gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)

    # Blur
    if params.get("blur", {}).get("enabled", True):
        ksize = params.get("blur", {}).get("kernel_size", 3)
        gray = cv2.GaussianBlur(gray, (ksize, ksize), 0)

    # Background cleaning
    bg_params = params.get("background_cleaning", {})
    taille_voisinage = bg_params.get("taille_voisinage", 10)
    tol = bg_params.get("tol", 25)
    pourcentage_similaire = bg_params.get("pourcentage_similaire", 0.35)
    cleaned = remove_uniform_background_by_similarity(gray, taille_voisinage, tol, pourcentage_similaire)

    # CLAHE
    clahe_params = params.get("clahe", {})
    clip_limit = clahe_params.get("clip_limit", 2.0)
    tile_grid = clahe_params.get("tile_grid_size", 8)
    clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=(tile_grid, tile_grid))
    enhanced = clahe.apply(cleaned)

    # Binarisation
    binar_params = params.get("binarization", {})
    if binar_params.get("enabled", False):
        enhanced = cv2.adaptiveThreshold(
            enhanced, 255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            binar_params.get("block_size", 11),
            binar_params.get("C", 2)
        )

    result = deskew(enhanced)
    return Image.fromarray(result)

def preprocess_pdf(pdf_path, save_images=True, debug=False, mode_doux=True, params=None):
    print(f"🔧 Prétraitement du PDF : {pdf_path}")
    raw_pages = convert_from_path(pdf_path, dpi=300)
    processed_pages = []

    if save_images:
        out_dir = "data/tmp_preprocessed"
        os.makedirs(out_dir, exist_ok=True)

    for i, pil_img in enumerate(raw_pages):
        processed = preprocess_page(pil_img, params=params)
        processed_pages.append(processed)

        if save_images:
            output_path = os.path.join("data/tmp_preprocessed", f"page_{i+1}.png")
            processed.save(output_path)
            print(f"📏 Sauvegardé : {output_path}")

        if debug:
            print(f"[👁️] Affichage de la page prétraitée {i + 1}")
            cv2.imshow("Prétraitement OCR", np.array(processed))
            cv2.waitKey(0)
            cv2.destroyAllWindows()

    return processed_pages