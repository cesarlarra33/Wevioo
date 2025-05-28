import os
import json
import argparse
from pdf2image import convert_from_path
import cv2
import numpy as np
from PIL import Image

def visualize_ocr_to_pdf(json_path, pdf_path=None, output_dir="data/ocr_visualization", image_dir=None):


    
    
    if image_dir:
        image_paths = sorted([
            os.path.join(image_dir, f) for f in os.listdir(image_dir)
            if f.lower().endswith('.png')
        ])
        pages = [Image.open(p) for p in image_paths]
    elif pdf_path:
        pages = convert_from_path(pdf_path, dpi=300)
    else:
        raise ValueError("❌ Vous devez fournir soit --image-dir, soit pdf_path.")

    
    with open(json_path, 'r', encoding='utf-8', errors='ignore') as f:
        ocr_data = json.load(f)

    
    os.makedirs(output_dir, exist_ok=True)
    if pdf_path:
        base_filename = os.path.splitext(os.path.basename(pdf_path))[0]
    elif image_dir:
        # Essaye de deviner un nom basé sur le JSON OCR (ex: nsia.json → nsia)
        base_filename = os.path.splitext(os.path.basename(json_path))[0]
    else:
        base_filename = "output"
    annotated_images = []

    for page_idx, page in enumerate(pages):
        img = cv2.cvtColor(np.array(page), cv2.COLOR_RGB2BGR)
        page_data = ocr_data[page_idx]

        for block in page_data.get("blocks", []):
            bx, by, bw, bh = block["x"], block["y"], block["width"], block["height"]
            cv2.rectangle(img, (bx, by), (bx + bw, by + bh), (255, 0, 0), 2)  # Red
            label = f"Bloc {block['block_num']} ({bx},{by}) {bw}x{bh}"
            cv2.putText(img, label, (bx, max(by - 10, 0)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 1)

            for line in block.get("lines", []):
                # 🔶 Délimitation de la ligne (bounding box)
                words = line.get("words", [])
                if not words:
                    continue
                x_min = min(w['x'] for w in words)
                y_min = min(w['y'] for w in words)
                x_max = max(w['x'] + w['width'] for w in words)
                y_max = max(w['y'] + w['height'] for w in words)

                cv2.rectangle(img, (x_min, y_min), (x_max, y_max), (0, 255, 255), 1)  # Jaune
                label = f"Ligne {line['line_num']}"
                cv2.putText(img, label, (x_min, max(y_min - 5, 0)), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 200, 200), 1)

                for word in words:
                    x, y, w, h = word["x"], word["y"], word["width"], word["height"]
                    cv2.rectangle(img, (x, y), (x + w, y + h), (0, 0, 255), 1)  # Bleu
                    label = f"({x},{y})"
                    cv2.putText(img, label, (x, max(y - 5, 0)), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 0, 255), 1)

        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        pil_img = Image.fromarray(img_rgb)
        annotated_images.append(pil_img)

    pdf_output_path = os.path.join(output_dir, f"{base_filename}_annotated.pdf")
    annotated_images[0].save(pdf_output_path, save_all=True, append_images=annotated_images[1:])
    print(f"✅ PDF annoté enregistré → {pdf_output_path}")
    
    # Nettoyage du dossier temporaire si utilisé
    if image_dir == "data/tmp_preprocessed":
        import shutil
        try:
            shutil.rmtree(image_dir)
            print(f"🧹 Dossier temporaire supprimé : {image_dir}")
        except Exception as e:
            print(f"⚠️ Impossible de supprimer {image_dir} : {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Génère un PDF avec les annotations OCR.")
    parser.add_argument("json_path", help="Chemin vers le JSON OCR structuré")
    parser.add_argument("pdf_path", nargs="?", default=None, help="Chemin vers le fichier PDF d'origine (optionnel si --image-dir est utilisé)")
    parser.add_argument("--output-dir", default="data/ocr_visualization", help="Répertoire de sortie pour le PDF annoté")
    parser.add_argument("--image-dir", help="Répertoire contenant les images prétraitées")
    

    args = parser.parse_args()
    visualize_ocr_to_pdf(
        json_path=args.json_path,
        pdf_path=args.pdf_path,
        output_dir=args.output_dir,
        image_dir=args.image_dir
        )

