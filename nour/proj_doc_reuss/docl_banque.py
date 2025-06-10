# manuel 
from docling.document_converter import DocumentConverter
import json
import pandas as pd
import re

# Configuration des banques
BANK_CONFIGS = {
    "nsia": {
        "name": "NSIA Banque",
        "table_separator": None,
        "text_filters": [],
        "table_processing": "standard"
    }, 
    "cbao": {
        "name": "CBAO",
        "table_separator": None,
        "text_filters": [],
        "table_processing": "standard"
    },

    "sgbe": {
        "name": "Societe general benin ",
        "table_separator": "!",
        "text_filters": [],
        "table_processing": "separator_split"      
    } , 
    "coris": {
        "name": "Coris banque",
        "table_separator": "!",
        "text_filters": [],
        "table_processing": "separator_split"      
    }

}

def choose_bank():
    """Permet à l'utilisateur de choisir sa banque"""
    print("Banques disponibles :")
    for key, config in BANK_CONFIGS.items():
        print(f"{key}: {config['name']}")
    
    while True:
        bank_choice = input("\nEntrez le code de votre banque : ").lower().strip()
        if bank_choice in BANK_CONFIGS:
            return bank_choice
        else:
            print("Code de banque invalide. Veuillez réessayer.")

def extract_texts_by_bank(texts, bank_config):
    """Extrait les textes selon la configuration de la banque"""
    extracted_texts = []
    
    for t in texts:
        text_content = t["text"].strip()
        
        # Filtrage selon les mots-clés de la banque
        if any(filter_word.lower() in text_content.lower() for filter_word in bank_config["text_filters"]):
            extracted_texts.append(text_content)
        elif len(text_content) > 10:  # Textes longs généralement importants
            extracted_texts.append(text_content)
    
    return extracted_texts

def extract_tables_by_bank(result, bank_config):
    """Extrait les tableaux selon la configuration de la banque"""
    extracted_tables = []
    
    if bank_config["table_processing"] == "standard":
        # Extraction standard des tableaux
        for table in result.document.tables:
            df = table.export_to_dataframe()
            extracted_tables.append(df.to_dict(orient="records"))
    
    elif bank_config["table_processing"] == "separator_split":
        # Extraction avec séparateur personnalisé
        separator = bank_config["table_separator"]
        
        # D'abord essayer l'extraction standard
        for table in result.document.tables:
            df = table.export_to_dataframe()
            extracted_tables.append(df.to_dict(orient="records"))
        
        # Puis chercher dans le texte pour les séparateurs
        full_text = ""
        for text_item in result.document.dict()["texts"]:
            full_text += text_item["text"] + "\n"
        
        if separator and separator in full_text:
            # Diviser le texte par séparateur
            text_sections = full_text.split(separator)
            for i, section in enumerate(text_sections):
                if section.strip():
                    extracted_tables.append({
                        "section": i,
                        "content": section.strip(),
                        "type": "text_section"
                    })
    
    return extracted_tables

def main():
    import json  # Assure que json est importé dans la fonction
    # Choix de la banque
    bank_code = choose_bank()
    bank_config = BANK_CONFIGS[bank_code]
    
    print(f"\nTraitement pour {bank_config['name']}...")
    
    # Demander le chemin du fichier
    file_path = input("Entrez le chemin du fichier PDF (ou appuyez sur Entrée pour 'pdfs/nsia.pdf') : ").strip()
    if not file_path:
        file_path = "pdfs/nsia.pdf"
    
    # Initialisation du convertisseur
    converter = DocumentConverter()
    result = converter.convert(file_path)
    
    # Extraction du texte et des tableaux
    results_body = result.document.dict()
    extracted_data = {
        "bank": bank_config["name"],
        "texts": [],
        "tables": []
    }
    
    # Récupération des textes selon la banque
    if "texts" in results_body:
        texts = results_body["texts"]
        extracted_data["texts"] = extract_texts_by_bank(texts, bank_config)

        # Traitement spécifique pour la banque "Societe general benin"
        if bank_code == "sgbe":
            header_line = "Date !      Libelle operation       ! Val !      Debit      !     Credit"
            
            start_index = None
            
            for i, line in enumerate(extracted_data["texts"]):
                if header_line in line:
                    start_index = i
                    break

            if start_index is not None:
                entete = extracted_data["texts"][:start_index]
                raw_table = extracted_data["texts"][start_index+1:]  # on saute la ligne-titre
            else:
                entete = extracted_data["texts"]
                raw_table = []

            # Transformation du tableau brut en objets structurés
            tableau = []
            for line in raw_table:
                parts = [part.strip() for part in line.replace(' ! ', '!')
                                      .replace('! ', '!')
                                      .replace(' !', '!')
                                      .split('!')]
             
    
                # Vérification du format (au moins date et libellé)
                if len(parts) >= 2:
                    transaction = {
                        "Date": parts[0],
                        "Libellé": parts[1],
                        "Date_val": parts[2] if len(parts) > 2 else "",
                        "Débit": parts[3] if len(parts) > 3 else "",
                        "Crédit": parts[4] if len(parts) > 4 else ""
                    }
                    tableau.append(transaction)

            parts1=re.split(r'\s{2,}', raw_table[-2] ) 
            transaction_1={

                "Type" : parts1[0] , "Debit" : parts1[1] , "Credit" : parts1[1] }
            
            parts2=re.split(r'\s{2,}', raw_table[-1] ) 
            transaction_2={

                "Type" : parts2[0] ,  "Credit" : parts2[1] }


                    
            sgbe_output = {
                "entete": entete,
                "tableau": tableau , 
                "Totaux" : [transaction_1, transaction_2]
            }

            with open("sgbe.json", "w", encoding="utf-8") as f:
                json.dump(sgbe_output, f, indent=2, ensure_ascii=False)

            print("Fichier structuré 'output_sgbe.json' généré.")
        
        




    # Extraction des tableaux selon la banque
    extracted_data["tables"] = extract_tables_by_bank(result, bank_config)
    
    # Affichage du résultat au format JSON
    print(f"\n=== Résultats pour {bank_config['name']} ===")
    print(json.dumps(extracted_data, indent=2, ensure_ascii=False))

    # Écriture dans un fichier JSON général
    with open(f"{bank_config['name']}.json", "w", encoding="utf-8") as f:
        json.dump(extracted_data, f, indent=2, ensure_ascii=False)
    
    return extracted_data

# Exécution du programme principal
if __name__ == "__main__":
    result = main()


