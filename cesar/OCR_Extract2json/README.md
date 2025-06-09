# OCR Parser de Relevés Bancaires Structurés

## Objectif du projet

Ce projet vise à extraire automatiquement des données structurées à partir de relevés bancaires PDF. Il permet de passer d’un fichier PDF brut à un JSON contenant des champs bien identifiés comme le numéro de compte, les soldes, les totaux, et la liste des transactions.

## Stratégie adoptée

Le pipeline d'analyse suit cette séquence :

1. OCR via Tesseract sur chaque page du PDF pour générer un fichier JSON décrivant chaque mot avec sa position.
2. Visualisation du résultat OCR avec surlignage des blocs, lignes, et mots, et remplissage d'un JSON non structuré contenant tout le texte du PDF.
3. Parsing du fichier JSON non structuré à l’aide de règles définies dans un fichier YAML propre à chaque type de document.
4. Transformation vers un JSON final structuré contenant les champs d’intérêt.

## Arborescence du projet

parsers/  
`extract_data.py` # script maître : prétraitement, OCR, parsing

`ocr_reader.py` # lance tesseract sur un PDF ou une image  

`table_cropper.py` # extrait les tableaux de transactions  

`preprocess_image.py` # fonctions de prétraitement d’image (sont appélées directement par ocr_reader)

`document_parser.py` # applique le YAML pour obtenir le JSON final  

scripts/  
`visualize_ocr.py` # génère un PDF annoté pour le debug  

configs/  
`*.releve.yaml` # règles de parsing pour chaque banque  

`data/raw/` # PDF sources  
`data/ocr/` # résultats OCR  
`data/tables_detected/` # tableaux découpés (optionnel)  
`data/ocr_visualization/` # PDF annotés  
`data/output/` # JSON structurés  

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


### Utilisation rapide

Le moyen le plus simple est le script maître :

```bash
python parsers/extract_data.py --pdf data/raw/mon_fichier.pdf --config configs/ma_banque.releve.yaml
```

Il prétraite le PDF si nécessaire, extrait les éventuels tableaux, lance
Tesseract puis applique le YAML pour produire `data/output/mon_fichier_structured.json`.

####  OCR d’un PDF → JSON brut

```bash
python parsers/ocr_reader.py data/raw/mon_fichier.pdf
```
- Sauvegarde le JSON OCR dans data/ocr/
- Génère automatiquement un PDF annoté dans data/ocr_visualization/

####  Parsing d’un OCR JSON → JSON structuré
```bash
python parsers/document_parser.py \
  --ocr-json data/ocr/mon_fichier.json \
  --yaml-config configs/nsia/releve.yaml \
  --output data/output/mon_fichier_structured.json
```
#### Visualiser manuellement un OCR
```bash
python scripts/visualize_ocr.py data/ocr/mon_fichier.json data/raw/mon_fichier.pdf
```

## Exemple

1. Ajouter un PDF dans data/raw/ (ex : nsia.pdf)
2. Lancer l'extraction : 
```bash
python parsers/extract_data.py --pdf data/raw/nsia.pdf --config configs/nsia.releve.yaml
```

##  À venir

- Détection automatique du type de document et de la banque de provenance pour pouvoir passer indéfféremment n'importe quel pdf à l'outil et qu'il utilise automatiquement le bon fichier de règles de parsing yaml. 
- Meilleure détection OCR sur les pdf mal scannés avec amélioration du preprocessing. 