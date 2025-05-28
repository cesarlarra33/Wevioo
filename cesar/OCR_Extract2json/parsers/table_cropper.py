import os
import cv2
import numpy as np
from pdf2image import convert_from_path
from preprocess_image import preprocess_page
from PIL import Image
import argparse

def detect_tables(image):
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
    else:
        gray = image.copy()

    _, binary = cv2.threshold(gray, 180, 255, cv2.THRESH_BINARY_INV)

    horiz_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (40, 1))
    horiz_lines = cv2.morphologyEx(binary, cv2.MORPH_OPEN, horiz_kernel, iterations=2)

    vert_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 40))
    vert_lines = cv2.morphologyEx(binary, cv2.MORPH_OPEN, vert_kernel, iterations=2)

    table_mask = cv2.add(horiz_lines, vert_lines)

    contours, _ = cv2.findContours(table_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    table_boxes = []
    for cnt in contours:
        x, y, w, h = cv2.boundingRect(cnt)
        if w > 100 and h > 50:
            table_boxes.append((x, y, w, h))

    return table_boxes


def crop_tables_from_pdf(pdf_path, output_dir="data/tables_detected", visualize=False, use_preprocessing=True):
    print(f"🔍 Traitement de : {pdf_path}")
    os.makedirs(output_dir, exist_ok=True)
    pages = convert_from_path(pdf_path, dpi=300)

    base_name = os.path.splitext(os.path.basename(pdf_path))[0]

    for page_num, pil_page in enumerate(pages):
        if use_preprocessing:
            processed = preprocess_page(pil_page)
        else:
            print("⚠️ Prétraitement désactivé — traitement sur l'image brute.")
            processed = pil_page

        image = np.array(processed)
        boxes = detect_tables(image)

        print(f"[📄] Page {page_num + 1} → {len(boxes)} tableau(x) détecté(s)")

        for i, (x, y, w, h) in enumerate(boxes):
            roi = image[y:y + h, x:x + w]
            roi_pil = Image.fromarray(roi)
            if roi_pil.mode != "RGB":
                roi_pil = roi_pil.convert("RGB")

            # Format du nom : nompdf_p1_tab1.pdf
            filename = f"{base_name}_p{page_num+1}_tab{i+1}.pdf"
            roi_path = os.path.join(output_dir, filename)
            roi_pil.save(roi_path, "PDF", resolution=300.0)
            print(f"   💾 Sauvegardé : {roi_path}")

        if visualize:
            annotated = image.copy()
            for (x, y, w, h) in boxes:
                cv2.rectangle(annotated, (x, y), (x + w, y + h), (0, 255, 0), 2)
            cv2.imshow(f"Page {page_num+1}", annotated)
            cv2.waitKey(0)
            cv2.destroyAllWindows()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Détecte et recadre les tableaux dans un PDF ou une image.")
    parser.add_argument("pdf_path", help="Chemin vers le PDF à traiter")
    parser.add_argument("--output-dir", default="data/tables_detected", help="Dossier où sauvegarder les tableaux")
    parser.add_argument("--visualize", action="store_true", help="Afficher les tableaux détectés")
    parser.add_argument("--no-preprocess", action="store_true", help="Désactiver le prétraitement de l'image")

    args = parser.parse_args()

    crop_tables_from_pdf(
        args.pdf_path,
        output_dir=args.output_dir,
        visualize=args.visualize,
        use_preprocessing=not args.no_preprocess
    )
