Lire doc (pdf electronqiue /scannée)  (algo reconnait les formats /les entités , pas obligatoire toutes les données par exp une facture (fournisseur / identifiant  de fournisseur / adresse / montant / les produits / tva /dates , pas  besoin (payement échelonnés / logo / le cachet) 

Les mettre dans Base de données  
 
Projet ancient : lire les factures si on lui dit cest ou le numero de point  , ca marche pour dizaines de factures . 


Astuce :  transformer pdf en image => mosque => trouver les zones x et y  

Notre projet :  ouvrir un écran , je l’envoie à un api et api renvoie le fichier json  
Prenons hop : Releves n’importe quel format  / pour les factures cest un peu compliqué 
Ideal : je precise rien et largo se débrouille 


2éme Algo  fait le matching  

Pour le relevé bancaire : num compte  bancaire /libellés 

Objectif : travailler sur les relevés bancaires   / pays : bénin  / créer  un api  (lire pdf et le traite et donne un json ) / on peut faire une api sur les factures et une api sur les releves bancaires . 

On peut prendre des hypotheses : lire une facture puis on sort un descripteur et on l’applique sur les autres factures de meme type 

Chercher des modèles pre entrainés sur des modèles de factures
