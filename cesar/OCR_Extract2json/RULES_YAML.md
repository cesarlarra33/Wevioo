# 📜 Mode d'emploi des fichiers de règles YAML

Ce document décrit toutes les options disponibles pour configurer l'extraction structurée de données OCR à partir de relevés bancaires, en utilisant des fichiers YAML.

---

## 🔧 Structure générale

```yaml
document_type: relevé_bancaire
banque: NOM_BANQUE
format: texte+tesseract

crop_tables: false                # Active/désactive la découpe automatique des tableaux
preprocess_pdf: false            # Applique ou non le prétraitement OCR sur le PDF principal
preprocess_tables: false         # Applique ou non le prétraitement OCR sur les tableaux extraits

ocr:
  pdf:
    psm: 3                        # Page Segmentation Mode pour le PDF
    oem: 3                        # OCR Engine Mode pour le PDF
  tables:
    psm: 12                       # PSM pour les tableaux (souvent utile pour lignes denses)
    oem: 1                        # OEM pour les tableaux
```

---

## 🧹 Champs simples

```yaml
structure:
  champs_simples:
    nom_du_champ:
      anchor: "Texte"                     # Mot-clé déclencheur (ancre simple)
      anchor_sequence: ["Mot1", "Mot2"]   # Ancre multiple (séquence de mots)
      direction: right                    # Méthode de recherche (voir tableau ci-dessous)
      regex: "\\d+"                       # Expression régulière pour extraire la valeur
      offset: 1                           # Décalage d'index depuis l’ancre
      concat: true                        # Concatène les mots correspondants
      concat_until: "FIN"                # Concatène jusqu'à ce mot
      min_x: 0                            # Position minimale X de recherche
      max_x: 2000                         # Position maximale X de recherche
      min_y: 0                            # Position minimale Y de recherche
      max_y: 2500                         # Position maximale Y de recherche
      tolerance_x: 10                     # Tolérance autour de l’ancre en X
      tolerance_y: 15                     # Tolérance autour de l’ancre en Y
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

---

## 📄 Transactions

```yaml
  transactions:
    source: "table"                      # ou "document"
    filter_contains: ["Date", "Libellé"]# Mots clés pour identifier le tableau à utiliser
    start_line_regex: "\\d{2}/\\d{2}/\\d{4}"  # Ligne de début de transaction
    start_line_x_max: 300
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

      date_valeur:
        x_min: 901
        x_max: 1100
        regex: "\\d{2}/\\d{2}/\\d{4}"

      mouv_debit:
        x_min: 1101
        x_max: 1300
        regex: "^\\d+(?: \\d{3})*(?:,\\d{2})?$"

      mouv_credit:
        x_min: 1301
        x_max: 1500
        regex: "^\\d+(?: \\d{3})*(?:,\\d{2})?$"
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
