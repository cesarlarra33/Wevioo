from docling.document_converter import DocumentConverter
import json
import pandas as pd
import re
import os
from test_2 import detecter_nom_banque_par_image

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
        "name": "Societe general benin",
        "table_separator": "!",
        "text_filters": [],
        "table_processing": "separator_split"      
    }, 
    "coris": {
        "name": "Coris banque",
        "table_separator": "!",
        "text_filters": [],
        "table_processing": "separator_split"      
    } , 
    "BIIC": {
        "name": "Banque Internationale pour l'Industrie et le Commerce",
        "table_separator": None,
        "text_filters": [],
        "table_processing": "standard"
    },
     "Ecobank": {
        "name": "Ecobank",
        "table_separator": None,
        "text_filters": [],
        "table_processing": "standard"
    },
     "Tresor": {
        "name": "Tresor",
        "table_separator": None,
        "text_filters": [],
        "table_processing": "standard"
    },
     "UBA BENIN": {
        "name": "UBA BENIN",
        "table_separator": None,
        "text_filters": [],
        "table_processing": "standard"
    },
    "BOA": {
        "name": "Bank of Africa",
        "table_separator": None,
        "text_filters": [],
        "table_processing": "standard"
    }
    
}

def is_empty_dict(d):
    """Vérifie si un dictionnaire est vide (toutes les valeurs sont vides ou None)"""
    if not isinstance(d, dict):
        return False
    
    for value in d.values():
        if value and str(value).strip():  # Si la valeur n'est pas vide et pas seulement des espaces
            return False
    return True

def clean_empty_dicts(data):
    """Supprime récursivement les dictionnaires vides d'une structure de données"""
    if isinstance(data, dict):
        # Nettoyer d'abord les valeurs du dictionnaire
        cleaned_dict = {}
        for key, value in data.items():
            cleaned_value = clean_empty_dicts(value)
            cleaned_dict[key] = cleaned_value
        return cleaned_dict
    
    elif isinstance(data, list):
        # Nettoyer la liste et supprimer les dictionnaires vides
        cleaned_list = []
        for item in data:
            cleaned_item = clean_empty_dicts(item)
            # N'ajouter que si ce n'est pas un dictionnaire vide
            if not is_empty_dict(cleaned_item):
                cleaned_list.append(cleaned_item)
        return cleaned_list
    
    else:
        # Pour les autres types, retourner tel quel
        return data

def detect_bank_from_pdf(file_path):
    """Détecte automatiquement la banque à partir du PDF"""
    try:
        print(f"Détection de la banque pour le fichier: {file_path}")
        detected_bank = detecter_nom_banque_par_image(file_path, debug=False)
        print(f"Banque détectée: {detected_bank}")
        
        # Normaliser le nom détecté pour le mapper avec la configuration
        if not detected_bank or detected_bank == "Banque non détectée":
            return None, None
            
        detected_bank_lower = detected_bank.lower().strip()
        
        # Recherche directe dans les clés
        if detected_bank_lower in BANK_CONFIGS:
            return detected_bank_lower, BANK_CONFIGS[detected_bank_lower]
        
        # Recherche par correspondance partielle
        for bank_key, config in BANK_CONFIGS.items():
            if bank_key in detected_bank_lower or detected_bank_lower in bank_key:
                return bank_key, config
        
        # Recherche par nom complet
        for bank_key, config in BANK_CONFIGS.items():
            if config["name"].lower() in detected_bank_lower or detected_bank_lower in config["name"].lower():
                return bank_key, config
        
        # Si aucune correspondance exacte, essayer avec des mots-clés
        if any(keyword in detected_bank_lower for keyword in ["société générale", "societe generale", "sgbe", "sg bénin", "sg benin"]):
            return "sgbe", BANK_CONFIGS["sgbe"]
        elif "nsia" in detected_bank_lower:
            return "nsia", BANK_CONFIGS["nsia"]
        elif "cbao" in detected_bank_lower:
            return "cbao", BANK_CONFIGS["cbao"]
        elif "coris" in detected_bank_lower:
            return "coris", BANK_CONFIGS["coris"]
        
        print(f"Attention: Banque '{detected_bank}' non reconnue dans la configuration")
        return None, None
        
    except Exception as e:
        print(f"Erreur lors de la détection de la banque: {e}")
        return None, None

def extract_texts_by_bank(texts, bank_config):
    """Extrait les textes selon la configuration de la banque"""
    extracted_texts = []
    
    for t in texts:
        text_content = t["text"].strip()
        
        # Filtrage selon les mots-clés de la banque (vérification si la liste n'est pas vide)
        if bank_config["text_filters"] and any(filter_word.lower() in text_content.lower() for filter_word in bank_config["text_filters"]):
            extracted_texts.append(text_content)
        elif len(text_content) > 10:  # Textes longs généralement importants
            extracted_texts.append(text_content)
    
    return extracted_texts

def extract_tables_by_bank(result, bank_config):
    """Extrait les tableaux selon la configuration de la banque"""
    extracted_tables = []
    
    try:
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
    except Exception as e:
        print(f"Erreur lors de l'extraction des tableaux : {e}")
    
    return extracted_tables

def process_sgbe_data(extracted_texts):
    """Traitement spécifique pour SGBE"""
    header_line = "Date !      Libelle operation       ! Val !      Debit      !     Credit"
    
    start_index = None
    
    for i, line in enumerate(extracted_texts):
        if header_line in line:
            start_index = i
            break
    
    if start_index is not None:
        entete = extracted_texts[:start_index]
        raw_table = extracted_texts[start_index+1:]  # on saute la ligne-titre
    else:
        entete = extracted_texts
        raw_table = []
    
    # Transformation du tableau brut en objets structurés
    tableau = []
    
    # Traiter les lignes de transaction normales (toutes sauf les 2 dernières si elles existent)
    transaction_lines = raw_table[:-2] if len(raw_table) >= 2 else raw_table
    
    for line in transaction_lines:
        if not line.strip():  # Ignorer les lignes vides
            continue
            
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
            # Ne pas ajouter si c'est un dictionnaire vide
            if not is_empty_dict(transaction):
                tableau.append(transaction)
    
    # Traitement des totaux (dernières lignes)
    totaux = []
    if len(raw_table) >= 2:
        try:
            # Traitement de l'avant-dernière ligne
            if raw_table[-2].strip():
                parts1 = re.split(r'\s{2,}', raw_table[-2].strip())
                if len(parts1) >= 2:
                    transaction_1 = {
                        "Type": parts1[0],
                        "Debit": parts1[1],
                        "Credit": parts1[2] if len(parts1) > 2 else ""
                    }
                    if not is_empty_dict(transaction_1):
                        totaux.append(transaction_1)
            
            # Traitement de la dernière ligne
            if raw_table[-1].strip():
                parts2 = re.split(r'\s{2,}', raw_table[-1].strip())
                if len(parts2) >= 2:
                    transaction_2 = {
                        "Type": parts2[0],
                        "Credit": parts2[1]
                    }
                    if not is_empty_dict(transaction_2):
                        totaux.append(transaction_2)
                    
        except (IndexError, Exception) as e:
            print(f"Erreur lors du traitement des totaux SGBE: {e}")
    
    return {
        "entete": entete,
        "tableau": tableau,
        "totaux": totaux
    }

def process_pdf(file_path, debug=False):
    try:
        # Vérifier que le fichier existe
        if not os.path.exists(file_path):
            print(f"Erreur : Le fichier '{file_path}' n'existe pas.")
            return None
        
        # Détection automatique de la banque
        bank_code, bank_config = detect_bank_from_pdf(file_path)
        
        if bank_config is None:
            print("Impossible de détecter la banque. Traitement annulé.")
            return None
        
        print(f"\nTraitement pour {bank_config['name']}...")
        
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
            sgbe_data = process_sgbe_data(extracted_data["texts"])
            
            # Nettoyer les dictionnaires vides
            cleaned_sgbe_data = clean_empty_dicts(sgbe_data)
            
            # Écriture directe du fichier uniquement avec les données traitées
            try:
                output_filename = "societe_general_benin.json"
                with open(output_filename, "w", encoding="utf-8") as f:
                    json.dump(cleaned_sgbe_data, f, indent=2, ensure_ascii=False)
                
                print(f"Fichier structuré '{output_filename}' généré avec les données traitées (dictionnaires vides supprimés).")
            except Exception as e:
                print(f"Erreur lors de l'écriture du fichier {output_filename} : {e}")
            
            return cleaned_sgbe_data

        # Extraction des tableaux selon la banque
        extracted_data["tables"] = extract_tables_by_bank(result, bank_config)
        
        # Nettoyer les dictionnaires vides dans les données extraites
        cleaned_extracted_data = clean_empty_dicts(extracted_data)
        
        # Traitement commun pour toutes les banques (affiché après traitement spécifique)
        print(f"\n=== Résultats pour {bank_config['name']} ===")
        print(json.dumps(cleaned_extracted_data, indent=2, ensure_ascii=False))
            
        # Écriture dans un fichier JSON général
        output_filename = f"{bank_config['name'].replace(' ', '_').lower()}.json"
        try:
            with open(output_filename, "w", encoding="utf-8") as f:
                json.dump(cleaned_extracted_data, f, indent=2, ensure_ascii=False)
                
            print(f"Fichier '{output_filename}' généré (dictionnaires vides supprimés).")
        except Exception as e:
            print(f"Erreur lors de l'écriture du fichier {output_filename} : {e}")
            
        return cleaned_extracted_data
        
    except Exception as e:
        print(f"Erreur lors du traitement : {e}")
        return None
