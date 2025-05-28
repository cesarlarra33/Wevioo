import os
import json
import argparse
import pytesseract
from pdf2image import convert_from_path
from pytesseract import Output
from collections import defaultdict
import subprocess
from preprocess_image import preprocess_pdf

pytesseract.pytesseract.tesseract_cmd = '/opt/homebrew/bin/tesseract'

def ocr_pdf_to_json(pdf_path, output_dir, use_preprocessing=True, psm=None, oem=None):
    if use_preprocessing:
        pages = preprocess_pdf(pdf_path, dpi=300, save_images=True, debug=False)
    else:
        print("⚠️ Prétraitement désactivé — OCR sur le PDF brut.")
        pages = convert_from_path(pdf_path, dpi=300)

    # Construction du paramètre config pour Tesseract
    config = ""
    if psm is not None:
        config += f"--psm {psm} "
    if oem is not None:
        config += f"--oem {oem}"

    results = []

    for page_num, image in enumerate(pages):
        ocr_data = pytesseract.image_to_data(
            image,
            output_type=Output.DICT,
            lang='fra',
            config=config.strip()
        )

        blocks = defaultdict(lambda: defaultdict(list))
        block_dimensions = {}

        for i in range(len(ocr_data['text'])):
            word = ocr_data['text'][i].strip()
            if not word:
                continue

            word_info = {
                "text": word,
                "x": ocr_data['left'][i],
                "y": ocr_data['top'][i],
                "width": ocr_data['width'][i],
                "height": ocr_data['height'][i],
                "page": page_num + 1,
                "line_num": ocr_data['line_num'][i],
                "block_num": ocr_data['block_num'][i],
                "word_num": ocr_data['word_num'][i],
                "conf": ocr_data['conf'][i]
            }

            block_id = ocr_data['block_num'][i]
            line_id = ocr_data['line_num'][i]
            blocks[block_id][line_id].append(word_info)

            if block_id not in block_dimensions:
                block_dimensions[block_id] = {
                    "x_min": word_info['x'],
                    "y_min": word_info['y'],
                    "x_max": word_info['x'] + word_info['width'],
                    "y_max": word_info['y'] + word_info['height']
                }
            else:
                dims = block_dimensions[block_id]
                dims['x_min'] = min(dims['x_min'], word_info['x'])
                dims['y_min'] = min(dims['y_min'], word_info['y'])
                dims['x_max'] = max(dims['x_max'], word_info['x'] + word_info['width'])
                dims['y_max'] = max(dims['y_max'], word_info['y'] + word_info['height'])

        page_blocks = []
        for block_id, lines in blocks.items():
            block_data = {
                "block_num": block_id,
                "x": block_dimensions[block_id]['x_min'],
                "y": block_dimensions[block_id]['y_min'],
                "width": block_dimensions[block_id]['x_max'] - block_dimensions[block_id]['x_min'],
                "height": block_dimensions[block_id]['y_max'] - block_dimensions[block_id]['y_min'],
                "lines": []
            }
            for line_id, words in lines.items():
                block_data["lines"].append({
                    "line_num": line_id,
                    "words": words
                })
            page_blocks.append(block_data)

        results.append({
            "page": page_num + 1,
            "blocks": page_blocks
        })

    os.makedirs(output_dir, exist_ok=True)
    base_name = os.path.basename(pdf_path).replace('.pdf', '.json')
    output_path = os.path.join(output_dir, base_name)

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"OCR terminé pour {pdf_path} → {output_path}")
    return output_path


# CLI
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="OCR un PDF et sauvegarder le résultat en JSON.")
    parser.add_argument("pdf_path", help="Chemin vers le fichier PDF à traiter")
    parser.add_argument("--output-dir", default="data/ocr", help="Répertoire où sauvegarder le JSON OCR")
    parser.add_argument("--no-preprocess", action="store_true", help="Désactiver le prétraitement OCR (contraste, binarisation, deskew)")
    parser.add_argument("--psm", type=int, help="Page Segmentation Mode de Tesseract (ex: 6, 11, 3...)")
    parser.add_argument("--oem", type=int, help="OCR Engine Mode (0=legacy, 1=LSTM, 2=combo, 3=default)")

    args = parser.parse_args()

    output_json_path = ocr_pdf_to_json(
        args.pdf_path,
        args.output_dir,
        use_preprocessing=not args.no_preprocess,
        psm=args.psm,
        oem=args.oem
    )

    # Visualisation automatique
    try:
        script_dir = os.path.dirname(__file__)
        visualize_script = os.path.join(script_dir, "../scripts", "visualize_ocr.py")
        command = ["python3", visualize_script, output_json_path]

        if not args.no_preprocess:
            command += ["--image-dir", "data/tmp_preprocessed"]
        else:
            command += [args.pdf_path]

        subprocess.run(command, check=True)

    except Exception as e:
        print(f"❌ Erreur lors de la visualisation OCR : {e}")
