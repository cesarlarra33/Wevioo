import pdfplumber

import re

text_tableau =[]
tableau =[] 

import pdfplumber
import re

with pdfplumber.open("pdfs/coris.pdf") as pdf:
    first_page = pdf.pages[0]
    text = first_page.extract_text()
    lines = text.split('\n')

    for i in range(1, 12):  # lignes 2 à 12 (index 1 à 11)
        raw_line = lines[i]

        # Supprimer les caractères indésirables : ! . - et tirets longs
        cleaned_line = re.sub(r'[!.\-]', '', raw_line)

        # Supprimer les espaces multiples → un seul
        cleaned_line = re.sub(r'\s{2,}', ' ', cleaned_line)

        # Supprimer les espaces en début et fin
        cleaned_line = cleaned_line.strip()

        # Sauter les lignes vides
        if cleaned_line:
            text_tableau.append (cleaned_line)
 



with pdfplumber.open("pdfs/coris.pdf") as pdf:
    lignes_a_ignorer = {}  # Dictionnaire pour stocker les lignes à ignorer par page
    
    for page_num, page in enumerate(pdf.pages, 1):
        text = page.extract_text()
        lines = text.split('\n')
        i = 0
        
        # Traitement normal des lignes (sauf pour la dernière page où on traite d'abord les lignes normales)
        while i < len(lines):
            # Vérifier si cette ligne doit être ignorée
            if page_num in lignes_a_ignorer and i in lignes_a_ignorer[page_num]:
                i += 1
                continue

            if 15 <= i <= len(lines)-1:
                # Éviter de traiter les lignes -4 et -2 dans le traitement normal si c'est la dernière page
                if page_num == len(pdf.pages) and (i == len(lines)-4 or i == len(lines)-2):
                    i += 1
                    continue
                    
                line = lines[i]
                if i == 15 and page == pdf.pages[0]:
                    l = [item for item in line.split("!") if item.strip() != ""]
                    transaction = {"Libelle": l[0], "Credit": l[1]}
                    tableau.append(transaction)
                else:
                    parts_1 = [part.strip() for part in line.replace(' ! ', '!')
                            .replace('! ', '!')
                            .replace(' !', '!')
                            .split('!')]
                    
                    # Vérification du format (au moins date et libellé)
                    if len(parts_1) >= 2:
                        transaction = {
                            "Date compta ": parts_1[1],
                            "Date valeur": parts_1[2],
                            "Utilisateur": parts_1[3] if len(parts_1) > 2 else "",
                            "NO piece": parts_1[4] if len(parts_1) > 3 else "",
                            "No eve": parts_1[5] if len(parts_1) > 4 else "",
                            "Ope": parts_1[6] if len(parts_1) > 5 else "",
                            "Libelle": parts_1[7] if len(parts_1) > 6 else "",
                            "Debit": parts_1[8] if len(parts_1) > 7 else "",
                            "Credit": parts_1[9] if len(parts_1) > 8 else ""
                        }
                        
                        # Si ce n'est pas la dernière ligne de la page
                        if i != len(lines) - 2:
                            
                            # Regrouper les lignes suivantes avec libellé complémentaire
                            j = i + 1
                            while j < len(lines):
                                next_line = lines[j]
                                next_parts = [part.strip() for part in next_line.replace(' ! ', '!')
                                            .replace('! ', '!')
                                            .replace(' !', '!')
                                            .split('!')]
                                print("nextparts",next_parts)
                                if len(next_parts) > 1 and next_parts[1] == "" and ( next_parts[8] == "" or  next_parts[9] == "") :
                                    transaction["Libelle"] += "\n" + next_parts[7]
                                    j += 1
                                else:
                                    break
                            tableau.append(transaction)
                            i = j
                            continue
                        
                        # Cas spécial : dernière ligne de la page
                        elif i == len(lines) - 2:
                            
                            # Vérifier s'il y a une page suivante
                            if page_num < len(pdf.pages):  # Correction : utiliser page_num au lieu de len(pdf.pages) > 1
                                
                                page_suivante = pdf.pages[page_num]  # page_num est déjà l'index correct
                                text_suivant = page_suivante.extract_text()
                                lignes_suivantes = text_suivant.split('\n')
                                
                                # Initialiser la liste des lignes à ignorer pour la page suivante
                                if (page_num + 1) not in lignes_a_ignorer:
                                    lignes_a_ignorer[page_num + 1] = []
                                
                                # Chercher les lignes complémentaires dans les premières lignes de la page suivante
                                j = 15
                                while j < 18:  # Vérifier max 3 lignes (15, 16, 17)
                                    if j >= len(lignes_suivantes):
                                        break
                                        
                                    ligne_suivante = lignes_suivantes[j]
                                 
                                    next_parts = [part.strip() for part in ligne_suivante.replace(' ! ', '!')
                                                .replace('! ', '!')
                                                .replace(' !', '!')
                                                .split('!')]
                               
                                    # Si c'est une ligne de libellé complémentaire
                                    if len(next_parts) > 1 and next_parts[1] == "":
                                        transaction["Libelle"] += "\n" + next_parts[7]
                                        lignes_a_ignorer[page_num + 1].append(j)  # Marquer cette ligne à ignorer
                                        j += 1
                                    else:
                                        break
                            
                            tableau.append(transaction)
                            i += 1
                            continue
            
            i += 1

        # Traiter les lignes -4 et -2 de la dernière page À LA FIN
        if page_num == len(pdf.pages):
            print("Traitement des lignes spéciales de la dernière page...")
            
            # Vérifier que les indices existent
            if len(lines) >= 4:
                ligne_moins_4 = lines[-4]
                ligne_moins_2 = lines[-2]
                
                for line_index, line in enumerate([ligne_moins_4, ligne_moins_2]):
                    print(f"Traitement ligne {-4 if line_index == 0 else -2}: {line}")
                    
                    l = [part.strip() for part in line.replace(' ! ', '!')
                                .replace('! ', '!')
                                .replace(' !', '!')
                                .split('!')]
                        
                    print(f"Parties extraites: {l}")

                    # Créer la transaction avec gestion des indices
                    transaction = {
                        "Libelle": l[7] if len(l) > 7 else "",
                        "Debit": l[8] if len(l) > 8 else "", 
                        "Credit": l[9] if len(l) > 9 else ""
                    }
                    print(f"Transaction créée: {transaction}")
                    tableau.append(transaction)
            else:
                print("Pas assez de lignes dans la dernière page pour extraire -4 et -2")





import json

# Structure du fichier final
output = {
    "texte": text_tableau,
    "transactions": tableau
}

# Écriture dans un fichier JSON
with open("coris.json", "w", encoding="utf-8") as f:
    json.dump(output, f, indent=4, ensure_ascii=False)