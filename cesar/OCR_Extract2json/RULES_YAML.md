# 📜 Mode d'emploi des fichiers de règles YAML

Ce document décrit toutes les options disponibles pour configurer l'extraction structurée de données OCR à partir de relevés bancaires, en utilisant des fichiers YAML.

---

## 🔧 Structure générale

```yaml
document_type: relevé_bancaire
banque: NOM_BANQUE
format: texte+tesseract

crop_tables: false            # Découpe les tableaux avant l'OCR
preprocess_pdf: false         # Prétraitement appliqué au PDF complet
preprocess_tables: false      # Prétraitement appliqué aux tableaux
preprocessing_params:         # (optionnel) réglages fins du prétraitement
  blur:
    enabled: true
    kernel_size: 3
  background_cleaning:
    taille_voisinage: 10
    tol: 25
    pourcentage_similaire: 0.35
  clahe:
    clip_limit: 2.0
    tile_grid_size: 8
  binarization:
    enabled: false
    block_size: 11
    C: 2

ocr:
  pdf:
    psm: 3                    # Page Segmentation Mode de Tesseract
    oem: 3                    # OCR Engine Mode
  tables:
    psm: 12                   # Paramètres propres aux tableaux
    oem: 1
```

## 🧹 Champs simples

```yaml
structure:
  champs_simples:
    nom_du_champ:
      anchor: "Texte"                # mot clé ancre
      anchor_sequence: ["Mot1","Mot2"]
      direction: right
      regex: "\\d+"
      offset: 1
      concat: true
      concat_until: "FIN"
      min_x: 0
      max_x: 2000
      min_y: 0
      max_y: 2500
      tolerance_x: 10
      tolerance_y: 15
```

> ⚠️ **Remarque importante** : les clés `x_min` / `x_max` sont utilisées uniquement dans les colonnes de tableaux pour les transactions. Dans les `champs_simples`, on utilise `min_x` / `max_x`. Il n'y a pas de distinction dans le code entre ces clés, c'est uniquement une convention contextuelle. Assurez-vous de rester cohérent selon le type de champ.

---

## 🛍️ Valeurs possibles pour `direction`

| Direction    | Description                                        |
| ------------ | -------------------------------------------------- |
| `right`      | Mot juste après l’ancre dans le flux OCR           |
| `line_right` | Mots à droite sur **la même ligne OCR**            |
| `right_xy`   | Mots à droite **(x > ancre)** avec tolérance sur Y |
| `nearby_xy`  | Mots proches de l’ancre (tolérance sur X et Y)     |
| `below`      | Mots situés juste en dessous de l’ancre            |
---

Deux modes sont possibles : **par colonnes** ou **with_separator**.

### Mode colonnes (par défaut)

```yaml
transactions:
  source: "table"                # ou "document"
  filter_contains: ["Date", "Libellé"]
  start_line_regex: "\\d{2}/\\d{2}/\\d{4}"
  start_line_x_min: 200
  start_line_x_max: 300
  start_line_y_min: 300
  start_line_y_max: 2400
  y_tolerance_above: 30
  y_tolerance_below: 40

  columns:
    date_transaction:
      x_min: 0
      x_max: 150
      regex: "\\d{2}/\\d{2}/\\d{4}"
    detail_transaction:
      x_min: 151
      x_max: 900
      concat: true
```

### Mode `with_separator`

```yaml
transactions:
  source: "document"
  mode: "with_separator"
  separator: "!"
  use_line_shape_heuristic: true
  line_shape_regex: "!(\\d{2}/\\d{2})![^!]+!(\\d{2}/\\d{2})!..."
  start_line_regex: "\\d{2}/\\d{2}"
  start_line_x_min: 280
  start_line_x_max: 310
  start_line_y_min: 300
  start_line_y_max: 2400
  y_tolerance: 5

  columns_order:
    - date_transaction
    - libelle
    - date_valeur
    - debit
    - credit

  columns_regex:
    date_transaction: "\\d{2}/\\d{2}"
    libelle: "[!1Il]?(.+?)(?=[!1Il]\\d{2}/\\d{2})"
    date_valeur: "[!1Il]?(?P<val>\\d{2}/\\d{2})"
    debit: (?<=[!])\\s*(\\d{1,3}(?:\\.\\d{3})*(?:,\\d{2})?)?\\s*(?=[!])
    credit: (?<=[!])\\s*(\\d{1,3}(?:\\.\\d{3})*(?:,\\d{2})?)?\\s*$    #permet d'eviter les erreurs ocr quand un l, i ou 1 à été lu à la place d'un ! 
```

---

## 🧼 Normalisation des données

```yaml
normalisation:
  montant:
    supprimer_espaces: true
    convertir_en_float: true

  date:
    format_source: "%d/%m/%Y"
    format_cible: "%Y-%m-%d"

  numero_de_compte:
    convertir_en_float: false
```

---

## 📌 Astuces utiles

* `anchor_sequence` permet d'éviter les faux positifs en utilisant plusieurs mots
* `offset` est utile pour ignorer des mots parasites juste après l'ancre
* `line_right` peut être fragile si l’OCR segmente mal les lignes, utiliser `right_xy` dans ce cas
* `concat_until` permet de capturer un bloc de texte jusqu’à une borne
* Les limites `min_x`, `max_x`, `min_y`, `max_y` servent à restreindre la zone de recherche d’ancre **et** de valeur
