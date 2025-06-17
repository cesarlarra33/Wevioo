import argparse
import os
import subprocess
import yaml
from pathlib import Path
import tempfile
import json

def charger_config_yaml(yaml_path):
    with open(yaml_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def construire_nom_base(pdf_path):
    return Path(pdf_path).stem

def lancer_ocr(pdf_path, psm, oem, preprocess=True, preprocessing_params=None):
    args = ["python3", "parsers/ocr_reader.py", pdf_path, "--psm", str(psm), "--oem", str(oem)]
    temp_file = None

    if not preprocess:
        args.append("--no-preprocess")
    elif preprocessing_params:
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".json", mode='w', encoding='utf-8')
        json.dump(preprocessing_params, temp_file)
        temp_file.close()
        args.extend(["--with-preprocessing-config", temp_file.name])

    try:
        subprocess.run(args, check=True)
    finally:
        if temp_file:
            os.remove(temp_file.name)

def lancer_crop_tables(pdf_path, preprocess=True):
    args = ["python3", "parsers/table_cropper.py", pdf_path]
    if not preprocess:
        args.append("--no-preprocess")
    subprocess.run(args, check=True)

def trouver_tableaux_detectes(nom_base):
    dossier_tables = Path("data/tables_detected")
    return sorted([str(p) for p in dossier_tables.glob(f"{nom_base}_p*_tab*.pdf")])

def lancer_parsing(ocr_json_path, yaml_path, output_path):
    args = [
        "python3", "parsers/document_parser.py",
        "--ocr-json", ocr_json_path,
        "--yaml-config", yaml_path,
        "--output", output_path
    ]
    subprocess.run(args, check=True)


def main():
    parser = argparse.ArgumentParser(
        description="Extraction de données depuis un PDF bancaire avec OCR et parsing YAML"
    )
    parser.add_argument("--pdf", required=True, help="Chemin vers le fichier PDF")
    parser.add_argument("--config", required=True, help="Fichier de configuration YAML")
    parser.add_argument("--output", required=False, help="Chemin de sortie du fichier JSON")
    args = parser.parse_args()

    config = charger_config_yaml(args.config)
    nom_base = construire_nom_base(args.pdf)

    print(f"📄 Fichier PDF : {args.pdf}")
    print(f"⚙️ Fichier de configuration : {args.config}")

    preprocess_pdf_flag = config.get("preprocess_pdf", False)
    preprocess_tables_flag = config.get("preprocess_tables", False)
    crop_tables = config.get("crop_tables", False)
    preprocessing_params = config.get("preprocessing_params")

    ocr_pdf_config = config.get("ocr", {}).get("pdf", {})
    psm_pdf = ocr_pdf_config.get("psm", 3)
    oem_pdf = ocr_pdf_config.get("oem", 3)

    ocr_tables_config = config.get("ocr", {}).get("tables", {})
    psm_tables = ocr_tables_config.get("psm", 3)
    oem_tables = ocr_tables_config.get("oem", 3)

    print("🔍 Lancement de l'OCR sur le PDF complet...")
    lancer_ocr(
        args.pdf,
        psm=psm_pdf,
        oem=oem_pdf,
        preprocess=preprocess_pdf_flag,
        preprocessing_params=preprocessing_params
    )

    if crop_tables:
        print("✂️ Découpage des tableaux...")
        lancer_crop_tables(args.pdf, preprocess=preprocess_pdf_flag)

        tableaux = trouver_tableaux_detectes(nom_base)
        print(f"📁 {len(tableaux)} tableau(x) trouvé(s)")
        for tab_path in tableaux:
            print(f"🔍 OCR sur le tableau : {tab_path}")
            lancer_ocr(
                tab_path,
                psm=psm_tables,
                oem=oem_tables,
                preprocess=preprocess_tables_flag,
                preprocessing_params=preprocessing_params
            )

    ocr_json_principal = f"data/ocr/{nom_base}.json"

    # 🔄 Gère la sortie personnalisée si elle est spécifiée
    output_path = args.output if args.output else f"data/output/{nom_base}_structured.json"

    print(f"🧬 Parsing des données OCR vers fichier structuré...")
    lancer_parsing(ocr_json_principal, args.config, output_path)
    print(f"✅ Extraction terminée → {output_path}")

if __name__ == "__main__":
    main()
