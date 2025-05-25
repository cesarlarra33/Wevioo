# OCR Parser de Relevés Bancaires Structurés

## Objectif du projet

Ce projet vise à extraire automatiquement des données structurées à partir de relevés bancaires PDF. Il permet de passer d’un fichier PDF brut à un JSON contenant des champs bien identifiés comme le numéro de compte, les soldes, les totaux, et la liste des transactions.

## Stratégie adoptée

Le pipeline d'analyse suit cette séquence :

1. OCR via Tesseract sur chaque page du PDF pour générer un fichier JSON décrivant chaque mot avec sa position.
2. Visualisation du résultat OCR avec surlignage des blocs, lignes, et mots.
3. Parsing du fichier OCR en JSON non structuré à l’aide de règles définies dans un fichier YAML propre à chaque type de document.
4. Transformation vers un JSON final structuré contenant les champs d’intérêt.

## Arborescence du projet

- data/raw/ : fichiers PDF sources
- data/ocr/ : fichiers OCR JSON générés
- data/ocr_visualization/ : versions annotées des fichiers PDF
- data/output/ : résultats finaux structurés en JSON
- configs/nsia/releve.yaml : règles spécifiques de parsing pour les relevés NSIA

## Installation


### 1. Créer un environnement virtuel
```bash 
python3 -m venv ocr_env
source ocr_env/bin/activate
```
### 2. Installer les dépendances
```bash
pip install -r requirements.txt
```
### 3. Installer Tesseract OCR + langue française

Ce projet nécessite que Tesseract soit installé et accessible à l’emplacement suivant :
```path
~/opt/homebrew/bin/tesseract
```
Sur macOS :

```bash
brew install tesseract
brew install tesseract-lang
```

Si ca marche pas, essayer : 
```bash 
curl -L -o /opt/homebrew/share/tessdata/fra.traineddata https://github.com/tesseract-ocr/tessdata/raw/master/fra.traineddata
``` 

Ne pas oublier d'ajouter le path à son ~/.bahsrc et refresh le terminal : 
```bash 
export TESSDATA_PREFIX=/opt/homebrew/share/tessdata/
source ~/.bashrc 
```

##  Utilisation des scripts

###  OCR d’un PDF → JSON brut

```bash
python parsers/ocr_reader.py data/raw/mon_fichier.pdf
```
- Sauvegarde le JSON OCR dans data/ocr/
- Génère automatiquement un PDF annoté dans data/ocr_visualization/

###  Parsing d’un OCR JSON → JSON structuré
```bash
python parsers/document_parser.py \
  --ocr-json data/ocr/mon_fichier.json \
  --yaml-config configs/nsia/releve.yaml \
  --output data/output/mon_fichier_structured.json
```
### Visualiser manuellement un OCR
```bash
python scripts/visualize_ocr.py data/ocr/mon_fichier.json data/raw/mon_fichier.pdf
```
##  Fichiers importants

- ocr_reader.py : applique Tesseract et structure les résultats OCR
- visualize_ocr.py : génère un PDF avec annotations des blocs/lines/mots
- document_parser.py : lit un OCR JSON + YAML pour produire un JSON final structuré
- configs/nsia/releve.yaml : règles pour identifier les champs des relevés NSIA

## Exemple

1. Ajouter un PDF dans data/raw/ (ex : nsia.pdf)
2. Lancer l’OCR : 
```bash
python parsers/ocr_reader.py data/raw/nsia.pdf
```
3. Lancer le parsing : 
```bash
python parsers/document_parser.py --ocr-json data/ocr/nsia.json --yaml-config configs/nsia/releve.yaml --output data/output/nsia_structured.json
```

##  À venir

- Support multi-banques via plusieurs fichiers YAML (pour factures et rélevés de différentes banques)
- Détection automatique des tableaux (peut être par IA avec table_detector.py)
- Détection automatique du type de document et de la banque de provenance pour pouvoir passer indéfféremment n'importe quel pdf à l'outil et qu'il utilise automatiquement le bon fichier de règles de parsing yaml. 
