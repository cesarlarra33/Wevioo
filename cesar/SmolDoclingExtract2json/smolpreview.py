import sys
from pathlib import Path
from PIL import Image
from pdf2image import convert_from_path

from mlx_vlm import load
from mlx_vlm.prompt_utils import apply_chat_template
from mlx_vlm.utils import load_config, stream_generate


# Chargement du modèle et de sa configuration
MODEL_PATH = "ds4sd/SmolDocling-256M-preview-mlx-bf16"
model, processor = load(MODEL_PATH)
config = load_config(MODEL_PATH)


def extract_raw_doctags(pdf_path: str):
    print(f"\n=== Analyse du PDF : {pdf_path}")

    images = convert_from_path(pdf_path)
    full_output = ""

    for i, image in enumerate(images):
        pil_image = image.convert("RGB")
        print(f"\n=== Traitement de la page {i+1}/{len(images)}")

        # Préparation du prompt
        prompt = "Extract this page as structured DocTag format. Detect tables as <otsl> blocks with <ched> headers and <fcel> cells Preserve key-value fields and layout coordinates."
        formatted_prompt = apply_chat_template(processor, config, prompt, num_images=1)

        # Génération DocTags
        output = ""
        for token in stream_generate(
            model, processor, formatted_prompt, [pil_image], max_tokens=4096, verbose=False
        ):
            output += token.text

        print(output)  # Affiche dans le terminal
        full_output += output + "\n"  # Ajoute un saut de ligne entre les pages

    # Définir le nom du fichier de sortie .txt
    output_path = Path("txt") / (Path(pdf_path).stem + ".txt")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(full_output)

    print(f"\n=== Extraction terminée. Résultat enregistré dans : {output_path}")


# Utilisation en ligne de commande
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("=== Usage : python3 smolpreview.py fichier.pdf")
        sys.exit(1)

    pdf_file = sys.argv[1]
    extract_raw_doctags(pdf_file)
