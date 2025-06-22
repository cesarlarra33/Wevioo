import argparse
from test_2 import detecter_nom_banque_par_image
from traiter_coris import main as traiter_coris
from tt_banques import process_pdf

def main():
    # Configuration de l'analyse des arguments en ligne de commande
    parser = argparse.ArgumentParser(description="Traitement des relevés bancaires")
    parser.add_argument("fichier_pdf", help="Chemin vers le fichier PDF à analyser")
    parser.add_argument("--debug", action="store_true", help="Activer le mode debug")
    args = parser.parse_args()

    # Étape 1: Détection de la banque
    print("\n=== Détection de la banque ===")
    nom_banque = detecter_nom_banque_par_image(args.fichier_pdf, debug=args.debug)
    print(f"Banque détectée: {nom_banque}")

    # Étape 2: Traitement spécifique ou générique selon la banque
    print("\n=== Traitement du PDF ===")
    if "coris" in nom_banque.lower():
        print("Traitement spécifique pour Coris Bank")
        traiter_coris()  # Note: Le fichier doit être nommé 'pdfs/coris.pdf'
    else:
        print("Traitement générique pour les autres banques")
        process_pdf(args.fichier_pdf, args.debug)  # Passez les deux arguments

if __name__ == "__main__":
    main()


# quand ilya API 
"""

# main.py
from test_2 import detecter_nom_banque_par_image
from traiter_coris import main as traiter_coris
from tt_banques import process_pdf

def traiter_pdf(fichier_pdf, debug=False):
    # Étape 1: Détection de la banque
    print("\n=== Détection de la banque ===")
    nom_banque = detecter_nom_banque_par_image(fichier_pdf, debug=debug)
    print(f"Banque détectée: {nom_banque}")

    # Étape 2: Traitement spécifique ou générique selon la banque
    print("\n=== Traitement du PDF ===")
    if "coris" in nom_banque.lower():
        print("Traitement spécifique pour Coris Bank")
        return traiter_coris()  # À corriger si besoin
    else:
        print("Traitement générique pour les autres banques")
        return process_pdf(fichier_pdf, debug)

# Garde la ligne de commande pour usage direct
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Traitement des relevés bancaires")
    parser.add_argument("fichier_pdf", help="Chemin vers le fichier PDF à analyser")
    parser.add_argument("--debug", action="store_true", help="Activer le mode debug")
    args = parser.parse_args()
    traiter_pdf(args.fichier_pdf, args.debug)"""
