import sys
import json
import os
from docling.document_converter import DocumentConverter  # bon chemin
import pandas as pd

def extract_pdf_to_json(pdf_path):
    print("📥 Initialisation du convertisseur...")
    converter = DocumentConverter()

    print(f"📥 Conversion du PDF: {pdf_path}")
    doc = converter.convert(pdf_path)
    print("✅ Conversion terminée.")

    # Extraction des textes
    print("🔍 Extraction du texte page par page...")
    pages_data = []
    for idx, page in enumerate(doc.pages):
        print(f"🔍 Page {idx + 1} sur {len(doc.pages)}")
        page_dict = {
            "number": page.page_number,
            "text": page.text,
            "blocks": [
                {
                    "text": block.text,
                    "bbox": block.bbox,
                    "lines": [
                        {
                            "text": line.text,
                            "bbox": line.bbox
                        } for line in block.lines
                    ]
                } for block in page.text_blocks
            ]
        }
        pages_data.append(page_dict)
    print("✅ Extraction du texte terminée.")

    # Extraction des tableaux
    print("🔍 Extraction des tableaux...")
    tables_json = []
    for i, table in enumerate(doc.tables):
        try:
            print(f"🧾 Export du tableau {i + 1} (page {table.page_number})")
            df = table.export_to_dataframe()
            table_json = {
                "table_id": i + 1,
                "page": table.page_number,
                "data": json.loads(df.to_json(orient="records"))
            }
            tables_json.append(table_json)
        except Exception as e:
            print(f"❌ Erreur lors de l'export du tableau {i+1} : {e}")
    print("✅ Extraction des tableaux terminée.")

    return {
        "file_name": os.path.basename(pdf_path),
        "num_pages": len(doc.pages),
        "pages": pages_data,
        "tables": tables_json
    }

def main():
    if len(sys.argv) != 2:
        print("Usage: python extract_docling_to_json.py <nom_du_fichier.pdf>")
        sys.exit(1)

    pdf_filename = sys.argv[1]

    print(f"📥 Vérification de l'existence du fichier : {pdf_filename}")
    if not os.path.exists(pdf_filename):
        print(f"❌ Erreur : le fichier {pdf_filename} n'existe pas.")
        sys.exit(1)

    output_dir = "json"
    os.makedirs(output_dir, exist_ok=True)
    print("📁 Dossier de sortie prêt.")

    print("🔁 Début du traitement du PDF...")
    data = extract_pdf_to_json(pdf_filename)

    pdf_base = os.path.splitext(os.path.basename(pdf_filename))[0]
    output_path = os.path.join(output_dir, f"{pdf_base}.json")

    print(f"💾 Sauvegarde dans : {output_path}")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"✅ Données extraites sauvegardées dans : {output_path}")

if __name__ == "__main__":
    main()
