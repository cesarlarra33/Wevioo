from docling.document_converter import DocumentConverter
import json
import pandas as pd
import re

def extract_sg_header_info(texts):
    """Extrait les informations d'en-tête spécifiques à SG"""
    header_info = {
        "periode": None,
        "numero_compte": None,
        "agence": None,
        "devise": None,
        "date_edition": None,
        "titulaire": None,
        "adresse": None
    }
    
    full_text = " ".join(texts)
    
    # Extraction de la période
    period_match = re.search(r'EXTRAIT DE COMPTE DU (\d{2}/\d{2}/\d{4})\s+AU (\d{2}/\d{2}/\d{4})', full_text)
    if period_match:
        header_info["periode"] = f"Du {period_match.group(1)} Au {period_match.group(2)}"
    
    # Extraction du numéro de compte (séquence de chiffres)
    account_match = re.search(r'(\d{10,})', full_text)
    if account_match:
        header_info["numero_compte"] = account_match.group(1)
    
    # Extraction de l'agence
    if "AGENCE PRINCIPALE" in full_text:
        header_info["agence"] = "AGENCE PRINCIPALE"
    
    # Extraction de la devise
    if "FRANC CFA BCEAO" in full_text:
        header_info["devise"] = "FRANC CFA BCEAO"
    
    # Extraction de la date d'édition
    date_match = re.search(r'(\d{1,2}\s+\w+\s+\d{4})\s+a\s+(\d{2}:\d{2})', full_text)
    if date_match:
        header_info["date_edition"] = f"{date_match.group(1)} à {date_match.group(2)}"
    
    # Extraction du titulaire (recherche de patterns de noms)
    name_patterns = re.findall(r'([A-Z]{2,}\s+[A-Z]{2,}(?:\s+[A-Z]{2,})*)', full_text)
    if name_patterns:
        # Filtrer les patterns qui ne sont pas des codes
        potential_names = [name for name in name_patterns if len(name) > 10 and not re.match(r'^[A-Z]{4,}\s*$', name)]
        if potential_names:
            header_info["titulaire"] = potential_names[0]
    
    return header_info

def parse_sg_transaction_line(line):
    """Parse une ligne de transaction SG avec séparateur !"""
    parts = line.split('!')
    
    if len(parts) < 3:
        return None
    
    # Nettoyage des parties
    parts = [part.strip() for part in parts if part.strip()]
    print(parts)
    
    transaction = {
        "Date": None,
        "Libelle operation": None,
        "Val": None,
        "Debit": None,
        "Credit": None,
        "solde": None
    }
    
    # Pattern typique: DATE!LIBELLE OPERATION!VAL!DEBIT!CREDIT
    if len(parts) >= 3:
        # Premier élément: date de transaction
        if re.match(r'\d{2}/\d{2}', parts[0]):
            transaction["Date"] = parts[0]
        
        # Deuxième élément: libellé
        transaction["Libelle operation"] = parts[1]
        
        # Troisième élément: date de valeur
        if len(parts) > 2 and re.match(r'\d{2}/\d{2}', parts[2]):
            transaction["Val"] = parts[2]
        
        # Traitement des montants - approche séquentielle
        amounts = []
        for i in range(3, len(parts)):
            part = parts[i]
            amount_match = re.search(r'[\d\s.,]+', part)

            if amount_match:
                amount_str = amount_match.group(0).replace(' ', '').replace(',', '.').strip()
                try:
                    value = float(amount_str)
                    amounts.append(str(value))
                except ValueError:
                    continue


        
        # Attribution des montants selon leur position
        # Format typique SG: DATE!LIBELLE!VAL!DEBIT!CREDIT!SOLDE
        if len(amounts) >= 1:
            # Si on a qu'un montant, déterminer s'il s'agit d'un débit ou crédit selon le libellé
            if len(amounts) == 1:
                libelle_upper = parts[1].upper()
                credit_keywords = ["VIREMENT", "DEPOT", "VERSEMENT", "CREDIT", "SALAIRE", "REMISE"]
                debit_keywords = ["RETRAIT", "COMMISSION", "FRAIS", "PAIEMENT", "CHEQUE", "DEBIT", "PRELEVEMENT"]

                if any(keyword in libelle_upper for keyword in credit_keywords):
                    transaction["Credit"] = amounts[0]
                else:
                    transaction["Debit"] = amounts[0]

            
            # Si on a 2 montants: premier = débit/crédit, second = solde
            elif len(amounts) == 2:
                libelle_upper = parts[1].upper()
                credit_keywords = ["VIREMENT", "DEPOT", "VERSEMENT", "CREDIT", "SALAIRE", "REMISE"]
                
                if any(keyword in libelle_upper for keyword in credit_keywords):
                    transaction["Credit"] = amounts[1]
                else:
                    transaction["Debit"] = amounts[0]
                transaction["solde"] = amounts[1]
            
            # Si on a 3 montants ou plus: DEBIT!CREDIT!SOLDE
            elif len(amounts) >= 3:
                transaction["Debit"] = amounts[0] if amounts[0] != "0" else None
                transaction["Credit"] = amounts[1] if amounts[1] != "0" else None
                transaction["solde"] = amounts[2]
    
    return transaction if any(transaction.values()) else None

def extract_sg_transactions(full_text):
    """Extrait les transactions SG à partir du texte complet"""
    transactions = []
    
    # Diviser par lignes et chercher les lignes avec !
    lines = full_text.split('\n')
    
    for line in lines:
        if '!' in line and len(line.strip()) > 10:
            # Vérifier si c'est une ligne de transaction (contient une date)
            if re.search(r'\d{2}/\d{2}', line):
                transaction = parse_sg_transaction_line(line)
                if transaction:
                    transactions.append(transaction)
    
    return transactions

def extract_sg_bank_statement(file_path):
    """Fonction principale pour extraire un relevé SG"""
    
    print("Traitement du relevé Société Générale...")
    
    # Initialisation du convertisseur
    converter = DocumentConverter()
    result = converter.convert(file_path)
    
    # Extraction du texte brut
    results_body = result.document.dict()
    all_texts = []
    
    if "texts" in results_body:
        texts = results_body["texts"]
        all_texts = [t["text"] for t in texts]
    
    # Combiner tout le texte
    full_text = "\n".join(all_texts)
    
    # Structure de données pour SG
    sg_data = {
        "banque": "Société Générale",
        "informations_compte": extract_sg_header_info(all_texts),
        "transactions": extract_sg_transactions(full_text),
        "texte_brut": full_text[:500] + "..." if len(full_text) > 500 else full_text  # Aperçu du texte
    }
    
    return sg_data

def test_transaction_parsing():
    """Fonction de test pour vérifier le parsing des transactions"""
    test_lines = [
        "31/01!COMMISSION DE CPTE AU 31/01/20!31/01!2500!!1500000",
        "15/02!VIREMENT SALAIRE!15/02!!50000!1550000",
        "20/03!RETRAIT DAB!20/03!10000!!1540000",
        "25/04!DEPOT ESPECES!25/04!!25000!1565000"
    ]
    
    print("🧪 TEST DU PARSING DES TRANSACTIONS:")
    print("="*50)
    
    for i, line in enumerate(test_lines, 1):
        print(f"\nTest {i}: {line}")
        result = parse_sg_transaction_line(line)
        if result:
            for key, value in result.items():
                if value:
                    print(f"   {key}: {value}")
        else:
            print("   ❌ Échec du parsing")
        print("-" * 30)

def main():
    """Programme principal"""
    
    # Option pour tester le parsing
    test_mode = input("Voulez-vous tester le parsing des transactions ? (o/n) : ").lower().strip()
    if test_mode == 'o':
        test_transaction_parsing()
        return
    
    # Demander le chemin du fichier
    file_path = input("Entrez le chemin du fichier PDF SG (ou appuyez sur Entrée pour 'pdfs/sg.pdf') : ").strip()
    if not file_path:
        file_path = "pdfs/sgbe.pdf"
    
    try:
        # Extraction des données
        result = extract_sg_bank_statement(file_path)
        
        # Affichage des résultats
        print("\n" + "="*50)
        print("RÉSULTATS EXTRACTION SOCIÉTÉ GÉNÉRALE")
        print("="*50)
        
        # Informations du compte
        print("\n📋 INFORMATIONS DU COMPTE:")
        for key, value in result["informations_compte"].items():
            if value:
                print(f"   {key.replace('_', ' ').title()}: {value}")
        
        # Transactions
        print(f"\n💰 TRANSACTIONS TROUVÉES: {len(result['transactions'])}")
        for i, transaction in enumerate(result["transactions"][:5], 1):  # Afficher les 5 premières
            print(f"\n   Transaction {i}:")
            for key, value in transaction.items():
                if value:
                    print(f"      {key}: {value}")
        
        if len(result["transactions"]) > 5:
            print(f"   ... et {len(result['transactions']) - 5} autres transactions")
        
        # Sauvegarde JSON
        output_file = "sgbe_extraction_result.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Résultats sauvegardés dans: {output_file}")
        
        return result
        
    except Exception as e:
        print(f"❌ Erreur lors du traitement: {str(e)}")
        return None

# Exécution du programme
if __name__ == "__main__":
    result = main()