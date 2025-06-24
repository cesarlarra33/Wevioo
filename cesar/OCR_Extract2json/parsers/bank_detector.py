# parsers/bank_detector.py

import fitz
import cv2
import numpy as np
from PIL import Image, ImageEnhance
import pytesseract
import io
import os
from typing import Optional

BANQUES_VARIANTES = {
    "nsia": ["nsia", "n.s.i.a", "nouvelle société", "interafricaine"],
    "coris": ["coris", "coris bank"],
    "cbao": ["cbao", "compagnie bancaire", "afrique occidentale"],
    "sgbe": ["sgbe", "société générale", "sg bénin", "sg benin", "societe generale"],
    "boa": ["boa", "bank of africa", "banque of africa"],
    "ecobank": ["ecobank", "eco bank"],
    "uba": ["uba", "united bank", "africa", "united bank for africa"],
    "orabank": ["orabank", "ora bank"],
    "bsic": ["bsic", "sahélo", "saharienne"],
    "diamond": ["diamond", "diamond bank"],
    "atlantic": ["atlantic", "atlantique"],
    "bgfi": ["bgfi", "gabonaise", "française"],
    "bia": ["bia", "internationale pour l'afrique"],
    "access": ["access", "access bank"],
    "gtbank": ["gtbank", "gt bank", "guaranty trust"],
    "tresor": ["trésor", "agence comptable centrale"],
    "biic": ["biic", "banque internationale pour l'industrie"]
}

def detect_bank_name(pdf_path: str, debug: bool = False) -> str:
    if not os.path.exists(pdf_path):
        return "inconnu"

    doc = fitz.open(pdf_path)
    if len(doc) == 0:
        doc.close()
        return "inconnu"

    page = doc[0]
    pix = page.get_pixmap(matrix=fitz.Matrix(3, 3))
    image = Image.open(io.BytesIO(pix.tobytes("png")))
    doc.close()

    width, height = image.size
    header = image.crop((0, 0, width, int(height * 0.25)))

    variantes_texte = []

    # Image originale
    variantes_texte.append(ocr(header))

    # Image contrastée
    variantes_texte.append(ocr(improve_contrast(header)))

    # Texte titres
    titres_img = extract_title_like_text(header)
    if titres_img:
        variantes_texte.append(ocr(titres_img))

    # Texte coloré
    couleur_img = extract_colored_text(header)
    if couleur_img:
        variantes_texte.append(ocr(couleur_img))

    for texte in variantes_texte:
        nom = analyser_texte_banque(texte)
        if nom:
            return nom

    return "inconnu"

def ocr(image: Image.Image) -> str:
    try:
        return pytesseract.image_to_string(image, config="--oem 3 --psm 6 -l fra+eng").lower()
    except:
        return ""

def improve_contrast(image: Image.Image) -> Image.Image:
    img = image.convert("L")
    img = ImageEnhance.Contrast(img).enhance(2.0)
    return ImageEnhance.Sharpness(img).enhance(2.0)

def extract_title_like_text(image: Image.Image) -> Optional[Image.Image]:
    try:
        img = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        binary = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                       cv2.THRESH_BINARY, 11, 2)
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        processed = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)

        contours, _ = cv2.findContours(processed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        mask = np.zeros_like(gray)

        for c in contours:
            x, y, w, h = cv2.boundingRect(c)
            if 100 < cv2.contourArea(c) < 50000 and h > 15 and w > 30 and h / w < 2:
                cv2.rectangle(mask, (x, y), (x + w, y + h), 255, -1)

        if np.sum(mask) > 0:
            result = cv2.bitwise_and(gray, mask)
            return Image.fromarray(result)
    except:
        pass
    return None

def extract_colored_text(image: Image.Image) -> Optional[Image.Image]:
    try:
        img = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

        masks = []
        masks.append(cv2.inRange(hsv, np.array([100, 50, 50]), np.array([130, 255, 255])))  # Bleu
        masks.append(cv2.bitwise_or(cv2.inRange(hsv, np.array([0, 50, 50]), np.array([10, 255, 255])),
                                    cv2.inRange(hsv, np.array([170, 50, 50]), np.array([180, 255, 255]))))  # Rouge
        masks.append(cv2.inRange(hsv, np.array([40, 50, 50]), np.array([80, 255, 255])))  # Vert

        mask = np.zeros_like(masks[0])
        for m in masks:
            mask = cv2.bitwise_or(mask, m)

        result = cv2.bitwise_and(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY), cv2.cvtColor(img, cv2.COLOR_BGR2GRAY), mask=mask)
        if np.sum(result) > 1000:
            return Image.fromarray(result)
    except:
        pass
    return None

def analyser_texte_banque(texte: str) -> Optional[str]:
    for banque, variantes in BANQUES_VARIANTES.items():
        for variante in variantes:
            if variante.lower() in texte:
                return banque
    return None
