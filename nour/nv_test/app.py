import streamlit as st
from traiter_coris import main as traiter_coris
from tt_banques import process_pdf
from test_2 import detecter_nom_banque_par_image
import tempfile
import os
import json

st.set_page_config(page_title="Analyse Relevé Bancaire", layout="wide")
st.title("📄 Extraction de données de relevés bancaires")

uploaded_file = st.file_uploader("Téléversez un relevé bancaire au format PDF", type="pdf")

if uploaded_file is not None:
    # Sauvegarde temporaire du fichier
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
        temp_file.write(uploaded_file.read())
        temp_file_path = temp_file.name
    
    st.success("✅ Fichier chargé avec succès.")
    st.write(f"📁 Fichier temporaire : {temp_file_path}")
    
    # Détection de la banque
    try:
        with st.spinner("🔍 Détection de la banque..."):
            nom_banque = detecter_nom_banque_par_image(temp_file_path, debug=False)
        
        st.info(f"🏦 Banque détectée : **{nom_banque}**")
        
        # Traitement selon la banque
        with st.spinner("⚙️ Traitement du relevé..."):
            if "coris" in nom_banque.lower():
                st.write("🔄 Traitement avec traiter_coris...")
                # CORRECTION: Passer le chemin du fichier à traiter_coris
                resultat = traiter_coris(temp_file_path)
            else:
                st.write("🔄 Traitement avec process_pdf...")
                resultat = process_pdf(temp_file_path, debug=False)
        
        # AJOUT: Debug information
        st.write(f"🔍 Debug - Type du résultat: {type(resultat)}")
        if resultat:
            st.write(f"🔍 Debug - Taille du résultat: {len(str(resultat))}")
        
        # Affichage du résultat
        if resultat:
            st.subheader("📤 Résultat JSON extrait")
            st.json(resultat)
            
            # Option de téléchargement JSON
            st.download_button(
                label="📥 Télécharger le JSON",
                data=json.dumps(resultat, indent=2, ensure_ascii=False),
                file_name="extraction_releve.json",
                mime="application/json"
            )
        else:
            st.error("❌ Le traitement a retourné un résultat vide.")
            st.write("🔍 Vérifiez que le fichier PDF contient du texte extractible.")
            st.write("🔍 Essayez avec un autre fichier PDF.")
    
    except Exception as e:
        st.error(f"❌ Erreur durant le traitement : {str(e)}")
        st.write("🔍 Détails de l'erreur :")
        st.code(str(e))
        
        # AJOUT: Plus d'informations de debug
        import traceback
        st.write("🔍 Traceback complet :")
        st.code(traceback.format_exc())
    
    finally:
        # Nettoyage du fichier temporaire
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)