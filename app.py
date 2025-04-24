import streamlit as st
import pandas as pd
from datetime import datetime
import altair as alt
import calendar
from utils import lire_onglet_excel, traiter_fichier, determiner_statut
from visualisation import creer_graphique_heures_par_employe, creer_graphiques_par_departement, creer_graphiques_tendance_journaliere, afficher_statut_employes

st.set_page_config(page_title="Calcul des Heures Employés", page_icon="⏱️")

# Initialiser l'état de session pour les rôles si ce n'est pas déjà fait
if 'employee_roles' not in st.session_state:
    st.session_state.employee_roles = {}

# Supprimer les constantes globales, elles seront calculées à partir des inputs
# SEUIL_CUISINE = 42 * 4.33 
# SEUIL_SALLE = 39 * 4.33

st.title("Calcul des Heures Employés")
st.markdown("Cet outil analyse un fichier Excel de pointage et calcule les heures travaillées par employé.")

# --- Paramètres d'analyse --- 
with st.sidebar:
    st.header("Paramètres des Seuils (Heures Supp.)")
    
    # Nouveaux inputs pour les seuils hebdomadaires par rôle
    seuil_hebdo_cuisine = st.number_input("Seuil Cuisine (heures/semaine)", 
                                          min_value=30.0, max_value=50.0, value=42.0, step=0.5,
                                          help="Seuil hebdomadaire pour déclencher les heures supplémentaires en Cuisine.")
    seuil_hebdo_salle = st.number_input("Seuil Salle (heures/semaine)", 
                                        min_value=30.0, max_value=50.0, value=39.0, step=0.5,
                                        help="Seuil hebdomadaire pour déclencher les heures supplémentaires en Salle.")
    
    # Calcul approximatif des seuils mensuels pour info
    approx_seuil_mensuel_cuisine = seuil_hebdo_cuisine * 4.33
    approx_seuil_mensuel_salle = seuil_hebdo_salle * 4.33
    st.info(f"Cuisine: ~{approx_seuil_mensuel_cuisine:.2f}h/mois")
    st.info(f"Salle: ~{approx_seuil_mensuel_salle:.2f}h/mois")
    
    st.divider()
    st.header("Autres Paramètres")

    # Garder le filtre par mois
    months_fr = ["Janvier", "Février", "Mars", "Avril", "Mai", "Juin", 
                "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"]
    mois_choisi = st.selectbox("Filtrer par mois", options=months_fr, index=datetime.now().month-1)
    mois_num = months_fr.index(mois_choisi) + 1
    
    # Garder la marge d'alerte
    marge_alerte = st.slider("Marge d'alerte (heures avant quota)", 
                           min_value=1, max_value=20, value=10,
                           help="Affiche une alerte orange quand l'employé approche de son quota spécifique (heures restantes)")
    
    montrer_toutes_donnees = st.checkbox("Montrer toutes les données si aucune donnée pour le mois sélectionné", value=False)

uploaded_file = st.file_uploader("Choisissez un fichier Excel (.xls, .xlsx)", type=["xls", "xlsx"])

onglet = st.text_input("Nom de l'onglet (ex: 'Enregistrement ')", value="Enregistrement ")

if uploaded_file is not None:
    try:
        # Calculer les seuils mensuels réels ici, une fois qu'on a les paramètres
        SEUIL_MENSUEL_CUISINE = seuil_hebdo_cuisine * 4.33
        SEUIL_MENSUEL_SALLE = seuil_hebdo_salle * 4.33
        SEUIL_DEFAUT_MOYEN = (SEUIL_MENSUEL_CUISINE + SEUIL_MENSUEL_SALLE) / 2
        
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
                    mois_disponibles = resultat_df['mois'].unique()
                    mois_disponibles_noms = [months_fr[m-1] for m in mois_disponibles]
                    if len(mois_disponibles) > 0:
                        st.subheader("Mois disponibles dans les données:")
                        cols = st.columns(len(mois_disponibles))
                        for i, (col, mois_nom) in enumerate(zip(cols, mois_disponibles_noms)):
                            with col:
                                st.metric(label=f"Mois {i+1}", value=mois_nom)
                    st.stop()
            
            # --- Section pour assigner les rôles ---
            st.subheader("Assigner les rôles (Cuisine/Salle)")
            roles_updated = False
            cols_roles = st.columns(2) 
            col_idx = 0
            
            unique_employees = filtered_df[['emp_id', 'name']].drop_duplicates().to_dict('records')

            if not unique_employees:
                 st.warning("Aucun employé trouvé dans les données filtrées pour assigner des rôles.")
            else:
                for emp in unique_employees:
                    emp_id = emp['emp_id']
                    emp_name = emp['name']
                    default_role_index = 0 
                    if emp_id in st.session_state.employee_roles:
                        if st.session_state.employee_roles[emp_id] == "Salle":
                            default_role_index = 1
                    else:
                        st.session_state.employee_roles[emp_id] = "Cuisine"
                    with cols_roles[col_idx % 2]:
                        selected_role = st.selectbox(
                            f"Rôle pour {emp_name} (ID: {emp_id})",
                            options=["Cuisine", "Salle"],
                            key=f"role_{emp_id}",
                            index=default_role_index 
                        )
                    if st.session_state.employee_roles[emp_id] != selected_role:
                        st.session_state.employee_roles[emp_id] = selected_role
                        roles_updated = True 
                    col_idx += 1

            # Ajouter la colonne 'Role' au DataFrame filtré principal
            filtered_df['Role'] = filtered_df['emp_id'].map(st.session_state.employee_roles)
            filtered_df['Role'].fillna("Non Assigné", inplace=True) 

            if roles_updated:
                 st.experimental_rerun()
            
            # --- Affichage des données journalières ---
            st.subheader(f"Aperçu des heures calculées - {mois_choisi}")
            st.dataframe(filtered_df[['emp_id', 'name', 'department', 'date', 'hours_worked', 'Role']])
            
            # --- Préparation du CSV ---
            csv = filtered_df.to_csv(index=False)
            st.download_button(
                label=f"Télécharger le CSV - {mois_choisi}",
                data=csv,
                file_name=f"heures_journalieres_{mois_choisi.lower()}.csv",
                mime="text/csv"
            )
            
            # --- Résumé par employé ---
            st.subheader(f"Résumé par employé - {mois_choisi}")
            resume = filtered_df.groupby(['emp_id', 'name', 'department', 'Role'])['hours_worked'].agg(['sum', 'mean', 'count']).reset_index()
            resume.columns = ['ID Employé', 'Nom', 'Département', 'Role', 'Heures Totales', 'Moyenne Quotidienne', 'Jours Travaillés']
            
            # Définir le seuil individuel basé sur le rôle et les SEUILS MENSUELS calculés
            def get_seuil(role):
                if role == "Cuisine":
                    return SEUIL_MENSUEL_CUISINE
                elif role == "Salle":
                    return SEUIL_MENSUEL_SALLE
                else:
                    # Utiliser la moyenne des seuils comme fallback pour "Non Assigné"
                    return SEUIL_DEFAUT_MOYEN 
            
            resume['Seuil Individuel'] = resume['Role'].apply(get_seuil)
            
            # Calculs basés sur le seuil individuel (inchangés)
            resume['Heures Supp'] = resume.apply(lambda x: max(0, x['Heures Totales'] - x['Seuil Individuel']), axis=1)
            resume['Heures Restantes'] = resume.apply(lambda x: max(0, x['Seuil Individuel'] - x['Heures Totales']), axis=1)
            resume['Statut'] = resume.apply(
                lambda x: determiner_statut(x['Heures Totales'], x['Seuil Individuel'], marge_alerte), 
                axis=1
            )
            
            # Afficher le résumé mis à jour (inchangé)
            st.dataframe(resume[['ID Employé', 'Nom', 'Département', 'Role', 'Heures Totales', 'Seuil Individuel', 'Heures Supp', 'Heures Restantes', 'Statut', 'Moyenne Quotidienne', 'Jours Travaillés']])
            
            # --- Affichage des statuts visuels ---
            st.subheader("Statut des heures supplémentaires")
            statut_df = resume.sort_values('Heures Totales', ascending=False)
            # Appel inchangé, la fonction utilise maintenant les données du df
            afficher_statut_employes(statut_df)
            
            # --- Graphiques --- 
            st.subheader("Visualisations")
            tab1, tab2, tab3 = st.tabs(["Heures totales par employé", "Heures par département", "Tendance journalière"])
            
            # Utiliser la moyenne des seuils pour la ligne de référence globale des graphiques
            seuil_ref_graphiques = SEUIL_DEFAUT_MOYEN
            # Calcul d'une moyenne journalière indicative pour le graphique de tendance
            heures_jour_ref = seuil_ref_graphiques / 21 # Approximation avec 21 jours/mois
            
            with tab1:
                st.subheader(f"Heures totales travaillées par employé - {mois_choisi}")
                # Passer la moyenne des seuils comme référence visuelle
                chart = creer_graphique_heures_par_employe(filtered_df, seuil_ref_graphiques)
                st.altair_chart(chart, use_container_width=True)
            
            with tab2:
                st.subheader(f"Heures travaillées par département - {mois_choisi}")
                # Passer la moyenne des seuils comme référence visuelle
                chart1, chart_combo, pie = creer_graphiques_par_departement(filtered_df, seuil_ref_graphiques)
                st.altair_chart(chart1, use_container_width=True)
                st.altair_chart(chart_combo, use_container_width=True)
                st.altair_chart(pie, use_container_width=True)
            
            with tab3:
                st.subheader(f"Tendance des heures travaillées par jour - {mois_choisi}")
                # Passer la moyenne journalière indicative comme référence
                chart, heatmap = creer_graphiques_tendance_journaliere(filtered_df, heures_jour_ref)
                st.altair_chart(chart, use_container_width=True)
                st.altair_chart(heatmap, use_container_width=True)
        else:
            st.warning("Aucune donnée trouvée dans le fichier.")
    
    except Exception as e:
        st.error(f"Erreur lors du traitement: {str(e)}")
        st.exception(e) 
else:
    st.info("Veuillez charger un fichier Excel pour commencer.")

# --- Informations supplémentaires --- 
with st.expander("À propos de l'application"):
    st.markdown(f"""
    Cette application analyse les fichiers de pointage et calcule les heures travaillées pour chaque employé.
    Elle prend en compte des seuils d'heures supplémentaires **configurables par rôle** (actuellement {seuil_hebdo_cuisine}h/semaine pour la Cuisine et {seuil_hebdo_salle}h/semaine pour la Salle).
    
    **Comment utiliser l'application:**
    1. Téléchargez votre fichier Excel de pointage.
    2. Vérifiez ou modifiez le nom de l'onglet si nécessaire.
    3. **Ajustez les seuils hebdomadaires pour la Cuisine et la Salle dans la barre latérale.**
    4. Définissez la marge d'alerte.
    5. **Assignez le rôle (Cuisine/Salle) à chaque employé dans la section dédiée.**
    6. L'application calculera les heures travaillées et le statut des heures supplémentaires basé sur le rôle et les seuils définis.
    7. Visualisez les résumés, statuts et graphiques.
    8. Téléchargez le résultat détaillé (incluant les rôles) au format CSV.
    """) 