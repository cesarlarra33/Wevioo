from docling.document_converter import DocumentConverter
import json
import pandas as pd

# Initialisation du convertisseur
converter = DocumentConverter()
result = converter.convert("pdfs/nsia.pdf")

# Extraction du texte et des tableaux
results_body = result.document.dict()
extracted_data = {
    "texts": [],
    "tables": []
}

# Récupération des textes
if "texts" in results_body:
    texts = results_body["texts"]
    for t in texts:
        text_content = t["text"]
        page = t["prov"][0]['page_no'] if "prov" in t and len(t["prov"]) > 0 and "page_no" in t["prov"][0] else "Unknown"
        extracted_data["texts"].append({
            "page": page,
            "content": text_content
        })

# Extraction des tableaux
for table in result.document.tables:
    df = table.export_to_dataframe()
    extracted_data["tables"].append(df.to_dict(orient="records"))

# Affichage du résultat au format JSON
print(json.dumps(extracted_data, indent=2, ensure_ascii=False))

# Écriture dans un fichier JSON
with open("nsia.json", "w", encoding="utf-8") as f:
    json.dump(extracted_data, f, indent=2, ensure_ascii=False)
    