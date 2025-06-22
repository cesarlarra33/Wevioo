import fitz  # PyMuPDF
import cv2
import numpy as np
from PIL import Image, ImageEnhance
import pytesseract
import re
from typing import Optional, Tuple
import io

def detecter_nom_banque_par_image(chemin_pdf: str, zone_haut_pct: float = 0.25, debug: bool = False) -> str:
    """
    Détecte le nom de la banque en analysant la zone haute de la première page
    avec focus sur les textes ayant des caractéristiques visuelles distinctives
    
    Args:
        chemin_pdf (str): Chemin vers le fichier PDF
        zone_haut_pct (float): Pourcentage de la page à analyser depuis le haut (0.25 = 25%)
        debug (bool): Affiche les images intermédiaires pour débogage
        
    Returns:
        str: Nom de la banque détecté
    """
    
    # Banques du Bénin et leurs variantes
    banques_connues = {
        "NSIA BANQUE": ["nsia", "n.s.i.a", "nouvelle société", "interafricaine"],
        "CORIS BANK": ["coris", "coris bank"],
        "CBAO BANQUE": ["cbao", "compagnie bancaire", "afrique occidentale"],
        "SGBE": ["sgbe", "société générale", "sg bénin", "sg benin", "societe generale"],
        "BOA BENIN": ["boa", "bank of africa", "banque of africa"],
        "ECOBANK BENIN": ["ecobank", "eco bank"],
        "UBA BENIN": ["uba", "united bank", "africa","United Bank for Africa"],
        "ORABANK": ["orabank", "ora bank"],
        "BSIC BENIN": ["bsic", "sahélo", "saharienne"],
        "DIAMOND BANK": ["diamond", "diamond bank"],
        "ATLANTIC BANK": ["atlantic", "atlantique"],
        "BGFI BANK": ["bgfi", "gabonaise", "française"],
        "BIA BENIN": ["bia", "internationale pour l'afrique"],
        "ACCESS BANK": ["access", "access bank"],
        "GTBANK BENIN": ["gtbank", "gt bank", "guaranty trust"] , 
        "Tresor": ["Agence Comptable Centrale du Trésor", "Trésor"],
        "BIIC": ["BIIC", "Banque Internationale pour l'Industrie et le Commerce"]
    }
    
    try:
        # Vérifier que le fichier existe
        import os
        if not os.path.exists(chemin_pdf):
            return f"Erreur: Fichier '{chemin_pdf}' non trouvé"
        
        # 1. Convertir la première page en image haute résolution
        doc = fitz.open(chemin_pdf)
        if len(doc) == 0:
            doc.close()
            return "Erreur: PDF vide"
            
        page = doc[0]
        
        # Zoom élevé pour une meilleure qualité
        zoom_matrix = fitz.Matrix(3, 3)  # Zoom x3
        pix = page.get_pixmap(matrix=zoom_matrix)
        img_data = pix.tobytes("png")
        
        # Convertir en image PIL
        image_complete = Image.open(io.BytesIO(img_data))
        width, height = image_complete.size
        
        # 2. Extraire la zone haute (header)
        zone_hauteur = int(height * zone_haut_pct)
        image_header = image_complete.crop((0, 0, width, zone_hauteur))
        
        if debug:
            try:
                image_header.save("debug_header_original.png")
                print(f"Image header extraite: {image_header.size}")
            except Exception as e:
                print(f"Erreur lors de la sauvegarde debug: {e}")
        
        doc.close()
        
        # 3. Analyser différentes variantes de l'image
        resultats_candidats = []
        
        # Initialiser les variables de texte
        texte_original = ""
        texte_contraste = ""
        texte_titres = ""
        texte_couleur = ""
        
        # Analyse 1: Image originale
        texte_original = extraire_texte_image(image_header)
        candidat = analyser_texte_banque(texte_original, banques_connues)
        if candidat:
            resultats_candidats.append((candidat, "original"))
        
        # Analyse 2: Amélioration du contraste
        try:
            image_contraste = ameliorer_contraste(image_header)
            if debug:
                image_contraste.save("debug_header_contraste.png")
            
            texte_contraste = extraire_texte_image(image_contraste)
            candidat = analyser_texte_banque(texte_contraste, banques_connues)
            if candidat and candidat not in [r[0] for r in resultats_candidats]:
                resultats_candidats.append((candidat, "contraste"))
        except Exception as e:
            if debug:
                print(f"Erreur analyse contraste: {e}")
        
        # Analyse 3: Détection de texte en gras/titre
        try:
            image_titres = detecter_texte_titre(image_header)
            if debug and image_titres is not None:
                image_titres.save("debug_header_titres.png")
            
            if image_titres:
                texte_titres = extraire_texte_image(image_titres)
                candidat = analyser_texte_banque(texte_titres, banques_connues)
                if candidat and candidat not in [r[0] for r in resultats_candidats]:
                    resultats_candidats.append((candidat, "titres"))
        except Exception as e:
            if debug:
                print(f"Erreur analyse titres: {e}")
        
        # Analyse 4: Détection par couleur (texte coloré/logo)
        try:
            image_couleur = detecter_texte_colore(image_header)
            if debug and image_couleur is not None:
                image_couleur.save("debug_header_couleur.png")
            
            if image_couleur:
                texte_couleur = extraire_texte_image(image_couleur)
                candidat = analyser_texte_banque(texte_couleur, banques_connues)
                if candidat and candidat not in [r[0] for r in resultats_candidats]:
                    resultats_candidats.append((candidat, "couleur"))
        except Exception as e:
            if debug:
                print(f"Erreur analyse couleur: {e}")
        
        if debug:
            print(f"Candidats trouvés: {resultats_candidats}")
            print(f"Texte original: {repr(texte_original[:200])}")
            print(f"Texte contraste: {repr(texte_contraste[:200])}")
        
        # Retourner le meilleur candidat
        if resultats_candidats:
            return resultats_candidats[0][0]
        
        # Si aucune banque spécifique trouvée, retourner le texte le plus probable
        tous_textes = [texte_original, texte_contraste, texte_titres, texte_couleur]
        for texte in tous_textes:
            if texte and len(texte.strip()) > 0:
                # Chercher des lignes qui ressemblent à des noms de banque
                lignes = texte.split('\n')
                for ligne in lignes[:5]:  # Premières lignes
                    ligne_clean = ligne.strip()
                    if (len(ligne_clean) > 5 and 
                        any(mot in ligne_clean.lower() for mot in ['bank', 'banque', 'société', 'compagnie', 'générale', 'generale']) and
                        len(ligne_clean) < 50):
                        return ligne_clean.upper()
        
        return "Banque non détectée"
        
    except Exception as e:
        return f"Erreur: {str(e)}"

def ameliorer_contraste(image: Image.Image) -> Image.Image:
    """Améliore le contraste pour mieux détecter le texte"""
    try:
        # Convertir en niveaux de gris
        if image.mode != 'L':
            image = image.convert('L')
        
        # Améliorer le contraste
        enhancer = ImageEnhance.Contrast(image)
        image = enhancer.enhance(2.0)
        
        # Améliorer la netteté
        enhancer = ImageEnhance.Sharpness(image)
        image = enhancer.enhance(2.0)
        
        return image
    except Exception as e:
        print(f"Erreur amélioration contraste: {e}")
        return image

def detecter_texte_titre(image: Image.Image) -> Optional[Image.Image]:
    """Détecte et isole le texte qui ressemble à des titres (gras, gros)"""
    try:
        # Convertir en OpenCV
        img_cv = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
        gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
        
        # Seuillage adaptatif pour isoler le texte
        binary = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                     cv2.THRESH_BINARY, 11, 2)
        
        # Opérations morphologiques pour connecter les lettres des titres
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        processed = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
        
        # Trouver les contours
        contours, _ = cv2.findContours(processed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # Créer un masque pour les gros éléments de texte
        mask = np.zeros_like(gray)
        
        # Filtrer les contours par taille (probablement des titres)
        min_area = 100
        max_area = 50000
        
        for contour in contours:
            area = cv2.contourArea(contour)
            if min_area < area < max_area:
                x, y, w, h = cv2.boundingRect(contour)
                # Filtrer par ratio (éviter les lignes très fines)
                if h > 15 and w > 30 and h/w < 2:
                    cv2.rectangle(mask, (x-2, y-2), (x+w+2, y+h+2), 255, -1)
        
        # Appliquer le masque
        result = cv2.bitwise_and(gray, mask)
        
        if np.sum(result) > 0:
            return Image.fromarray(result)
        
        return None
        
    except Exception as e:
        print(f"Erreur détection texte titre: {e}")
        return None

def detecter_texte_colore(image: Image.Image) -> Optional[Image.Image]:
    """Détecte le texte coloré qui pourrait être un logo/nom de banque"""
    try:
        img_cv = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
        hsv = cv2.cvtColor(img_cv, cv2.COLOR_BGR2HSV)
        
        # Masques pour différentes couleurs courantes des banques
        masques = []
        
        # Bleu (couleur courante des banques)
        lower_blue = np.array([100, 50, 50])
        upper_blue = np.array([130, 255, 255])
        mask_blue = cv2.inRange(hsv, lower_blue, upper_blue)
        masques.append(mask_blue)
        
        # Rouge
        lower_red1 = np.array([0, 50, 50])
        upper_red1 = np.array([10, 255, 255])
        lower_red2 = np.array([170, 50, 50])
        upper_red2 = np.array([180, 255, 255])
        mask_red = cv2.bitwise_or(cv2.inRange(hsv, lower_red1, upper_red1),
                                 cv2.inRange(hsv, lower_red2, upper_red2))
        masques.append(mask_red)
        
        # Vert
        lower_green = np.array([40, 50, 50])
        upper_green = np.array([80, 255, 255])
        mask_green = cv2.inRange(hsv, lower_green, upper_green)
        masques.append(mask_green)
        
        # Combiner tous les masques
        mask_final = np.zeros_like(mask_blue)
        for mask in masques:
            mask_final = cv2.bitwise_or(mask_final, mask)
        
        # Opérations morphologiques pour nettoyer
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
        mask_final = cv2.morphologyEx(mask_final, cv2.MORPH_CLOSE, kernel)
        
        # Appliquer le masque à l'image en niveaux de gris
        gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
        result = cv2.bitwise_and(gray, gray, mask=mask_final)
        
        if np.sum(result) > 1000:  # Seuil minimum de pixels colorés
            return Image.fromarray(result)
        
        return None
        
    except Exception as e:
        print(f"Erreur détection texte coloré: {e}")
        return None

def extraire_texte_image(image: Image.Image) -> str:
    """Extrait le texte d'une image avec OCR optimisé"""
    try:
        # Configuration OCR pour le français
        config = '--oem 3 --psm 6 -l fra+eng'
        texte = pytesseract.image_to_string(image, config=config)
        return texte
    except Exception as e:
        print(f"Erreur extraction texte: {e}")
        return ""

def analyser_texte_banque(texte: str, banques_connues: dict) -> Optional[str]:
    """Analyse le texte extrait pour identifier une banque"""
    if not texte:
        return None
    
    texte_lower = texte.lower()
    
    # Recherche directe des banques connues
    for nom_banque, variantes in banques_connues.items():
        for variante in variantes:
            if variante.lower() in texte_lower:
                return nom_banque
    
    return None

