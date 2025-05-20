import layoutparser as lp
from pdf2image import convert_from_path
from PIL import Image

# Charger une page du PDF
images = convert_from_path("cboa.pdf")
image = images[0]  # Une seule page pour le test

# Charger le modèle pré-entraîné PubLayNet
model = lp.Detectron2LayoutModel('lp://PubLayNet/mask_rcnn_R_50_FPN_3x/config')

# Détection des blocs de layout
layout = model.detect(image)

# Afficher l'image avec les boîtes détectées
lp.draw_box(image, layout).show()
