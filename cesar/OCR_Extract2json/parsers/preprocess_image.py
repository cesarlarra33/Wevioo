import cv2
import numpy as np
from pdf2image import convert_from_path
from pytesseract import image_to_osd, Output
from PIL import Image
import os

'''
Ce script fait un preprocessing pour améliorer la qualité du PDF :
- augmente le contraste localement (CLAHE)
- réduit le bruit léger (flou gaussien)
- blanchit les zones grisées du fond (si localement trop de pixels similaires)
- binarise (noir/blanc sans gris)
- redresse le texte (deskew)
'''

def deskew(image):
    try:
        osd = image_to_osd(image, output_type=Output.DICT)
        angle = float(osd.get("rotate", 0))

        # Appliquer deskew seulement si angle modéré (5 à 20 degrés)
        if abs(angle) < 5 or abs(angle) > 20:
            print(f"[ℹ️] Rotation ignorée (angle détecté : {angle}°)")
            return image

        (h, w) = image.shape[:2]
        center = (w // 2, h // 2)
        rot_mat = cv2.getRotationMatrix2D(center, -angle, 1.0)
        rotated = cv2.warpAffine(image, rot_mat, (w, h), flags=cv2.INTER_LINEAR)
        print(f"[↪] Rotation appliquée : {-angle}°")
        return rotated

    except Exception as e:
        print(f"[!] Deskew failed: {e}")
    return image

def remove_uniform_background_by_similarity(gray, taille_voisinage=15, tol=10, pourcentage_similaire=0.85):
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

def preprocess_page(pil_img, mode_doux=False):
    img = np.array(pil_img)
    gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
    blurred = cv2.GaussianBlur(gray, (3, 3), 0)

    # 🧼 Nettoyage des zones de fond uniforme avant le CLAHE
    cleaned = remove_uniform_background_by_similarity(
        blurred,
        taille_voisinage=8,
        tol=25,
        pourcentage_similaire=0.35
    )

    # 🌪️ Contraste local
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(cleaned)

    # 🌚 Binarisation
    """ if mode_doux:
        thresh = cv2.adaptiveThreshold(
            enhanced, 255,
            cv2.ADAPTIVE_THRESH_MEAN_C,
            cv2.THRESH_BINARY,
            25, 10
        )
    else:
        thresh = cv2.adaptiveThreshold(
            enhanced, 255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            11, 2
        ) """

    # ➡️ Deskew (redressement)
    result = deskew(enhanced)
    return Image.fromarray(result)

def preprocess_pdf(pdf_path, dpi=300, save_images=True, debug=False, mode_doux=True):
    print(f"🔧 Prétraitement du PDF : {pdf_path}")
    raw_pages = convert_from_path(pdf_path, dpi=dpi)
    processed_pages = []

    if save_images:
        out_dir = "data/tmp_preprocessed"
        os.makedirs(out_dir, exist_ok=True)

    for i, pil_img in enumerate(raw_pages):
        processed = preprocess_page(pil_img, mode_doux=mode_doux)
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