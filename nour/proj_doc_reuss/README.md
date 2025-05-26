# Vue globale

Ce projet consiste à développer un algorithme spécifique pour chaque type de banque.  
Chaque banque peut avoir un format de relevé différent, donc un traitement adapté est nécessaire.

---

# `docl`

Ce dossier contient des fichiers JSON extraits à partir des PDF, structurés par page.

Exemple de structure :

```json
{
  "texts": [
    {
      "page": 1,
      "content": "RELEVE DE COMPTE"
    }
  ]
}

voir ficher nsia.json

# docl_sans_pages 

j'ia fait une petite correction : 

"texts": 
    "RELEVE DE COMPTE",
    "Du 01/11/2024 Au 30/11/2024",
    "Numéro de Compte",

voir le fichier nsia_sans_pages.json 


# docl_banque  

c'est un ficher general pour tous les banques , je lai teste sur nsia , cbao et sgbe : 

voir nsia banque_sans_pages.json  , cboa_sans_pages.json  et societe general benin_sans_pages 

# sgbe_script 

cest un script  pour la banque sgbe  , !! il manque qq ameliorations 