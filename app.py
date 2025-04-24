import streamlit as st
import pandas as pd
from datetime import datetime
import altair as alt
import calendar
from utils import lire_onglet_excel, traiter_fichier, determiner_statut
from visualisation import creer_graphique_heures_par_employe, creer_graphiques_par_departement, creer_graphiques_tendance_journaliere, afficher_statut_employes

st.set_page_config(page_title="Calcul des Heures Employés", page_icon="⏱️")

st.title("Calcul des Heures Employés")
st.markdown("Cet outil analyse un fichier Excel de pointage et calcule les heures travaillées par employé.")

# Paramètres d'analyse
with st.sidebar:
    st.header("Paramètres")
    heures_standard = st.number_input("Heures standard par mois (avant heures supp.)", 
                                     min_value=35.0, max_value=200.0, value=151.67, step=1.0,
                                     help="Seuil des heures standard mensuelles (151.67h = 35h/semaine)")
    
    months_fr = ["Janvier", "Février", "Mars", "Avril", "Mai", "Juin", 
                "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"]
    
    mois_choisi = st.selectbox("Filtrer par mois", options=months_fr, index=datetime.now().month-1)
    mois_num = months_fr.index(mois_choisi) + 1
    
    jours_ouvres = st.slider("Jours ouvrés dans le mois", min_value=18, max_value=23, value=21)
    heures_jour = round(heures_standard / jours_ouvres, 2)
    st.info(f"Moyenne par jour ouvré: {heures_jour:.2f}h")
    
    # Seuil d'alerte pour approche du quota
    marge_alerte = st.slider("Marge d'alerte (heures avant quota)", 
                           min_value=1, max_value=20, value=10,
                           help="Affiche une alerte orange quand l'employé approche du quota (heures restantes)")
    
    montrer_toutes_donnees = st.checkbox("Montrer toutes les données si aucune donnée pour le mois sélectionné", value=False)

uploaded_file = st.file_uploader("Choisissez un fichier Excel (.xls, .xlsx)", type=["xls", "xlsx"])

onglet = st.text_input("Nom de l'onglet (ex: 'Enregistrement ')", value="Enregistrement ")

if uploaded_file is not None:
    try:
        with st.spinner('Analyse du fichier en cours...'):
            resultat_df = traiter_fichier(uploaded_file, onglet)
        
        if not resultat_df.empty:
            st.success("Traitement terminé avec succès!")
            
            # Conversion et filtrage par mois
            resultat_df['date'] = pd.to_datetime(resultat_df['date'])
            resultat_df['mois'] = resultat_df['date'].dt.month
            
            # Filtrer par mois si spécifié
            filtered_df = resultat_df.copy()
            if mois_num:
                filtered_df = resultat_df[resultat_df['mois'] == mois_num]
                
            if filtered_df.empty:
                if montrer_toutes_donnees:
                    st.warning(f"Aucune donnée disponible pour {mois_choisi}. Affichage de toutes les données.")
                    filtered_df = resultat_df
                else:
                    st.warning(f"⚠️ Aucune donnée disponible pour le mois de {mois_choisi}.")
                    st.info("Pour voir toutes les données, activez l'option 'Montrer toutes les données' dans la barre latérale.")
                    
                    # Affichage des mois disponibles
                    mois_disponibles = resultat_df['mois'].unique()
                    mois_disponibles_noms = [months_fr[m-1] for m in mois_disponibles]
                    
                    if len(mois_disponibles) > 0:
                        st.subheader("Mois disponibles dans les données:")
                        cols = st.columns(len(mois_disponibles))
                        for i, (col, mois_nom) in enumerate(zip(cols, mois_disponibles_noms)):
                            with col:
                                st.metric(label=f"Mois {i+1}", value=mois_nom)
                    
                    # Arrête le traitement
                    st.stop()
            
            # Affichage des résultats filtrés
            st.subheader(f"Aperçu des heures calculées - {mois_choisi}")
            st.dataframe(filtered_df[['emp_id', 'name', 'department', 'date', 'hours_worked']])
            
            # Préparation du CSV pour téléchargement
            csv = filtered_df.to_csv(index=False)
            
            # Bouton de téléchargement
            st.download_button(
                label=f"Télécharger le CSV - {mois_choisi}",
                data=csv,
                file_name=f"heures_journalieres_{mois_choisi.lower()}.csv",
                mime="text/csv"
            )
            
            # Résumé par employé
            st.subheader(f"Résumé par employé - {mois_choisi}")
            resume = filtered_df.groupby(['emp_id', 'name', 'department'])['hours_worked'].agg(['sum', 'mean', 'count']).reset_index()
            resume.columns = ['ID Employé', 'Nom', 'Département', 'Heures Totales', 'Moyenne Quotidienne', 'Jours Travaillés']
            st.dataframe(resume)
            
            # Vérification des heures supplémentaires
            resume['Heures Supp'] = resume['Heures Totales'] - heures_standard
            resume['Heures Restantes'] = heures_standard - resume['Heures Totales']
            resume['Heures Supp'] = resume['Heures Supp'].apply(lambda x: max(0, x))
            
            # Statut basé sur les heures restantes ou supplémentaires
            resume['Statut'] = resume.apply(
                lambda x: determiner_statut(x['Heures Totales'], heures_standard, marge_alerte), 
                axis=1
            )
            
            # Affichage des statuts d'heures supp dans un tableau visuel
            st.subheader("Statut des heures supplémentaires")
            
            # Création d'un tableau visuel avec des indicateurs colorés
            statut_df = resume.sort_values('Heures Totales', ascending=False)
            
            # Utilisation de la fonction du module visualisation
            afficher_statut_employes(statut_df, heures_standard)
            
            # Graphiques
            st.subheader("Visualisations")
            
            # Onglets pour différentes visualisations
            tab1, tab2, tab3 = st.tabs(["Heures totales par employé", "Heures par département", "Tendance journalière"])
            
            with tab1:
                st.subheader(f"Heures totales travaillées par employé - {mois_choisi}")
                
                # Utilisation de la fonction du module visualisation
                chart = creer_graphique_heures_par_employe(filtered_df, heures_standard)
                st.altair_chart(chart, use_container_width=True)
            
            with tab2:
                st.subheader(f"Heures travaillées par département - {mois_choisi}")
                
                # Utilisation de la fonction du module visualisation
                chart1, chart_combo, pie = creer_graphiques_par_departement(filtered_df, heures_standard)
                
                st.altair_chart(chart1, use_container_width=True)
                st.altair_chart(chart_combo, use_container_width=True)
                st.altair_chart(pie, use_container_width=True)
            
            with tab3:
                st.subheader(f"Tendance des heures travaillées par jour - {mois_choisi}")
                
                # Utilisation de la fonction du module visualisation
                chart, heatmap = creer_graphiques_tendance_journaliere(filtered_df, heures_jour)
                
                st.altair_chart(chart, use_container_width=True)
                st.altair_chart(heatmap, use_container_width=True)
        else:
            st.warning("Aucune donnée trouvée dans le fichier.")
    
    except Exception as e:
        st.error(f"Erreur lors du traitement: {str(e)}")
else:
    st.info("Veuillez charger un fichier Excel pour commencer.")

# Informations supplémentaires
with st.expander("À propos de l'application"):
    st.markdown("""
    Cette application analyse les fichiers de pointage et calcule les heures travaillées pour chaque employé.
    
    **Comment utiliser l'application:**
    1. Téléchargez votre fichier Excel de pointage
    2. Vérifiez ou modifiez le nom de l'onglet si nécessaire
    3. Utilisez les paramètres dans la barre latérale pour définir les seuils d'heures standard
    4. L'application calculera automatiquement les heures travaillées et identifiera les heures supplémentaires
    5. Téléchargez le résultat au format CSV
    """) 