import pdfplumber
import re
import json

# Initialisation des variables globales
text_tableau = []
tableau = []

def is_empty_transaction(transaction):
    """Vérifie si une transaction est vide (tous les champs sont vides ou contiennent seulement des espaces)"""
    for key, value in transaction.items():
        if isinstance(value, str) and value.strip():
            return False
    return True

def extract_header_data(pdf_path):
    """Extrait les données de l'en-tête (lignes 2 à 12 de la première page)"""
    with pdfplumber.open(pdf_path) as pdf:
        if not pdf.pages:
            print("Erreur: Le PDF est vide")
            return
            
        first_page = pdf.pages[0]
        text = first_page.extract_text()
        
        if not text:
            print("Erreur: Impossible d'extraire le texte de la première page")
            return
            
        lines = text.split('\n')
        
        # Vérifier qu'il y a assez de lignes
        if len(lines) < 12:
            print(f"Attention: Seulement {len(lines)} lignes trouvées, moins que les 12 attendues")
            
        # Traiter les lignes 2 à 12 (index 1 à 11)
        for i in range(1, min(12, len(lines))):
            raw_line = lines[i]
            
            # Supprimer les caractères indésirables : ! . - et tirets longs
            cleaned_line = re.sub(r'[!.\-—–]', '', raw_line)
            
            # Supprimer les espaces multiples → un seul
            cleaned_line = re.sub(r'\s{2,}', ' ', cleaned_line)
            
            # Supprimer les espaces en début et fin
            cleaned_line = cleaned_line.strip()
            
            # Sauter les lignes vides
            if cleaned_line:
                text_tableau.append(cleaned_line)

def extract_transactions(pdf_path):
    """Extrait les transactions du PDF"""
    with pdfplumber.open(pdf_path) as pdf:
        lignes_a_ignorer = {}  # Dictionnaire pour stocker les lignes à ignorer par page
        
        for page_num, page in enumerate(pdf.pages, 1):
            text = page.extract_text()
            
            if not text:
                print(f"Attention: Impossible d'extraire le texte de la page {page_num}")
                continue
                
            lines = text.split('\n')
            i = 0
            
            while i < len(lines):
                # Vérifier si cette ligne doit être ignorée
                if page_num in lignes_a_ignorer and i in lignes_a_ignorer[page_num]:
                    i += 1
                    continue

                # Traiter les lignes de 15 à la fin (sauf dernières lignes spéciales)
                if 15 <= i < len(lines):
                    # Éviter de traiter les lignes -4 et -2 dans le traitement normal si c'est la dernière page
                    if page_num == len(pdf.pages) and (i == len(lines)-4 or i == len(lines)-2):
                        i += 1
                        continue
                    
                    line = lines[i]
                    
                    # Cas spécial pour la ligne 15 de la première page
                    if i == 15 and page_num == 1:
                        parts = [item.strip() for item in line.split("!") if item.strip()]
                        if len(parts) >= 2:
                            transaction = {
                                "Libelle": parts[0],
                                "Credit": parts[1]
                            }
                            # Ajouter seulement si la transaction n'est pas vide
                            if not is_empty_transaction(transaction):
                                tableau.append(transaction)
                    else:
                        # Traitement normal des autres lignes
                        parts_1 = [part.strip() for part in line.replace(' ! ', '!')
                                .replace('! ', '!')
                                .replace(' !', '!')
                                .split('!')]
                        
                        # Vérification du format (au moins 2 parties)
                        if len(parts_1) >= 2:
                            transaction = {
                                "Date compta": parts_1[1] if len(parts_1) > 1 else "",
                                "Date valeur": parts_1[2] if len(parts_1) > 2 else "",
                                "Utilisateur": parts_1[3] if len(parts_1) > 3 else "",
                                "NO piece": parts_1[4] if len(parts_1) > 4 else "",
                                "No eve": parts_1[5] if len(parts_1) > 5 else "",
                                "Ope": parts_1[6] if len(parts_1) > 6 else "",
                                "Libelle": parts_1[7] if len(parts_1) > 7 else "",
                                "Debit": parts_1[8] if len(parts_1) > 8 else "",
                                "Credit": parts_1[9] if len(parts_1) > 9 else ""
                            }
                            
                            # Si ce n'est pas la dernière ligne de la page
                            if i < len(lines) - 2:
                                # Regrouper les lignes suivantes avec libellé complémentaire
                                j = i + 1
                                while j < len(lines) - 1:  # Éviter la dernière ligne
                                    next_line = lines[j]
                                    next_parts = [part.strip() for part in next_line.replace(' ! ', '!')
                                                .replace('! ', '!')
                                                .replace(' !', '!')
                                                .split('!')]
                                    
                                    # Vérifier si c'est une ligne de complément
                                    if (len(next_parts) > 8 and 
                                        len(next_parts[1]) == 0 and 
                                        (len(next_parts[8]) == 0 or len(next_parts[9]) == 0)):
                                        
                                        if len(next_parts) > 7:
                                            transaction["Libelle"] += "\n" + next_parts[7]
                                        j += 1
                                    else:
                                        break
                                
                                # Ajouter seulement si la transaction n'est pas vide
                                if not is_empty_transaction(transaction):
                                    tableau.append(transaction)
                                i = j
                                continue
                            
                            # Cas spécial : avant-dernière ligne de la page
                            elif i == len(lines) - 2:
                                # Vérifier s'il y a une page suivante
                                if page_num < len(pdf.pages):
                                    next_page = pdf.pages[page_num]  # Index correct
                                    text_suivant = next_page.extract_text()
                                    
                                    if text_suivant:
                                        lignes_suivantes = text_suivant.split('\n')
                                        
                                        # Initialiser la liste des lignes à ignorer pour la page suivante
                                        if (page_num + 1) not in lignes_a_ignorer:
                                            lignes_a_ignorer[page_num + 1] = []
                                        
                                        # Chercher les lignes complémentaires
                                        j = 15
                                        while j < min(18, len(lignes_suivantes)):
                                            ligne_suivante = lignes_suivantes[j]
                                            next_parts = [part.strip() for part in ligne_suivante.replace(' ! ', '!')
                                                        .replace('! ', '!')
                                                        .replace(' !', '!')
                                                        .split('!')]
                                            
                                            # Si c'est une ligne de libellé complémentaire
                                            if (len(next_parts) > 8 and 
                                                len(next_parts[1]) == 0 and
                                                len(next_parts) > 7):
                                                transaction["Libelle"] += "\n" + next_parts[7]
                                                lignes_a_ignorer[page_num + 1].append(j)
                                                j += 1
                                            else:
                                                break
                                
                                # Ajouter seulement si la transaction n'est pas vide
                                if not is_empty_transaction(transaction):
                                    tableau.append(transaction)
                
                i += 1

            # Traiter les lignes spéciales de la dernière page
            if page_num == len(pdf.pages) and len(lines) >= 4:
                print("Traitement des lignes spéciales de la dernière page...")
                
                special_lines = [lines[-4], lines[-2]]
                
                for line_index, line in enumerate(special_lines):
                    print(f"Traitement ligne {-4 if line_index == 0 else -2}: {line}")
                    
                    parts = [part.strip() for part in line.replace(' ! ', '!')
                                .replace('! ', '!')
                                .replace(' !', '!')
                                .split('!')]
                    
                    print(f"Parties extraites: {parts}")

                    # Créer la transaction avec gestion sécurisée des indices
                    transaction = {
                        "Libelle": parts[7] if len(parts) > 7 else "",
                        "Debit": parts[8] if len(parts) > 8 else "", 
                        "Credit": parts[9] if len(parts) > 9 else ""
                    }
                    
                    # Ajouter seulement si la transaction n'est pas vide
                    if not is_empty_transaction(transaction):
                        print(f"Transaction créée: {transaction}")
                        tableau.append(transaction)


def main(pdf_path=None):  # CHANGEMENT: Accepter un paramètre optionnel
    """Fonction principale"""
    global text_tableau, tableau
    text_tableau = []
    tableau = []

    # CHANGEMENT: Utiliser le paramètre fourni ou le chemin par défaut
    if pdf_path is None:
        pdf_path = "pdfs/coris.pdf"  # Chemin par défaut pour la compatibilité
    
    try:
        extract_header_data(pdf_path)
        extract_transactions(pdf_path)

        transactions_filtrees = [t for t in tableau if not is_empty_transaction(t)]

        output = {
            "texte": text_tableau,
            "transactions": transactions_filtrees
        }

        # (facultatif) Enregistrement local
        # with open("coris.json", "w", encoding="utf-8") as f:
        #     json.dump(output, f, indent=4, ensure_ascii=False)

        return output

    except FileNotFoundError:
        raise FileNotFoundError(f"Fichier introuvable : {pdf_path}")
    except Exception as e:
        raise Exception(f"Erreur lors de l'extraction : {e}")

if __name__ == "__main__":
    main()