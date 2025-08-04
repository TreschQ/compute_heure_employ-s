import streamlit as st
import pandas as pd
from datetime import datetime
import altair as alt
import calendar
from utils import lire_onglet_excel, traiter_fichier, determiner_statut
from visualisation import creer_graphique_heures_par_employe, creer_graphiques_par_departement, creer_graphiques_tendance_journaliere, afficher_statut_employes

st.set_page_config(page_title="Calcul des Heures Employés", page_icon="⏱️")

# Initialiser l'état de session pour les rôles et modifications manuelles si ce n'est pas déjà fait
if 'employee_roles' not in st.session_state:
    st.session_state.employee_roles = {}
if 'manual_adjustments' not in st.session_state:
    st.session_state.manual_adjustments = {}

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
            
            # Appliquer les modifications manuelles aux données
            def apply_manual_adjustments(df):
                """Applique les modifications manuelles aux heures travaillées"""
                df_adjusted = df.copy()
                for key, new_hours in st.session_state.manual_adjustments.items():
                    emp_id, date_str = key.split('|')
                    mask = (df_adjusted['emp_id'] == emp_id) & (df_adjusted['date'].dt.strftime('%Y-%m-%d') == date_str)
                    df_adjusted.loc[mask, 'hours_worked'] = new_hours
                return df_adjusted
            
            # Appliquer les ajustements manuels
            adjusted_df = apply_manual_adjustments(filtered_df)
            
            # --- Section d'édition manuelle des heures ---
            st.subheader("🔧 Édition manuelle des heures")
            st.markdown("*Modifiez les heures pour corriger les problèmes de pointeuse (ex: après minuit)*")
            
            with st.expander("Modifier les heures d'un employé", expanded=False):
                # Sélection de l'employé
                employees_options = [(f"{row['name']} (ID: {row['emp_id']})", row['emp_id']) 
                                   for _, row in filtered_df[['emp_id', 'name']].drop_duplicates().iterrows()]
                
                if employees_options:
                    selected_option = st.selectbox(
                        "Choisir un employé",
                        options=employees_options,
                        format_func=lambda x: x[0]
                    )
                    selected_emp_display, selected_emp_id = selected_option
                    
                    # Récupérer les données de l'employé sélectionné
                    emp_data = filtered_df[filtered_df['emp_id'] == selected_emp_id].copy()
                    emp_data = emp_data.sort_values('date')
                    
                    if not emp_data.empty:
                        st.write(f"**Heures actuelles pour {emp_data.iloc[0]['name']}:**")
                        
                        # Créer une interface d'édition pour chaque jour
                        cols = st.columns(3)
                        col_idx = 0
                        
                        for idx, row in emp_data.iterrows():
                            date_str = row['date'].strftime('%Y-%m-%d')
                            date_display = row['date'].strftime('%d/%m/%Y')
                            key = f"{selected_emp_id}|{date_str}"
                            
                            with cols[col_idx % 3]:
                                # Valeur actuelle (originale ou modifiée)
                                current_value = st.session_state.manual_adjustments.get(key, row['hours_worked'])
                                
                                new_hours = st.number_input(
                                    f"{date_display}",
                                    min_value=0.0,
                                    max_value=24.0,
                                    value=float(current_value),
                                    step=0.25,
                                    key=f"edit_{key}",
                                    help=f"Heures originales: {row['hours_worked']:.2f}h"
                                )
                                
                                # Sauvegarder la modification si différente de l'original
                                if abs(new_hours - row['hours_worked']) > 0.01:  # Tolérance pour les erreurs de virgule flottante
                                    st.session_state.manual_adjustments[key] = new_hours
                                    st.success(f"✓ Modifié")
                                elif key in st.session_state.manual_adjustments and abs(new_hours - row['hours_worked']) <= 0.01:
                                    # Restaurer à la valeur originale
                                    del st.session_state.manual_adjustments[key]
                                
                            col_idx += 1
                        
                        # Bouton pour réinitialiser toutes les modifications de cet employé
                        if st.button(f"Réinitialiser toutes les heures de {emp_data.iloc[0]['name']}", key=f"reset_{selected_emp_id}"):
                            keys_to_remove = [k for k in st.session_state.manual_adjustments.keys() 
                                            if k.startswith(f"{selected_emp_id}|")]
                            for k in keys_to_remove:
                                del st.session_state.manual_adjustments[k]
                            st.experimental_rerun()
                
                # Afficher le résumé des modifications
                if st.session_state.manual_adjustments:
                    st.subheader("📝 Résumé des modifications")
                    modifications_data = []
                    for key, new_hours in st.session_state.manual_adjustments.items():
                        emp_id, date_str = key.split('|')
                        emp_name = filtered_df[filtered_df['emp_id'] == emp_id]['name'].iloc[0]
                        original_hours = filtered_df[
                            (filtered_df['emp_id'] == emp_id) & 
                            (filtered_df['date'].dt.strftime('%Y-%m-%d') == date_str)
                        ]['hours_worked'].iloc[0]
                        
                        modifications_data.append({
                            'Employé': emp_name,
                            'Date': pd.to_datetime(date_str).strftime('%d/%m/%Y'),
                            'Heures originales': f"{original_hours:.2f}",
                            'Heures modifiées': f"{new_hours:.2f}",
                            'Différence': f"{new_hours - original_hours:+.2f}"
                        })
                    
                    if modifications_data:
                        st.dataframe(pd.DataFrame(modifications_data), use_container_width=True)
                        
                        if st.button("🗑️ Réinitialiser toutes les modifications"):
                            st.session_state.manual_adjustments = {}
                            st.experimental_rerun()
            
            # --- Affichage des données journalières (avec modifications) ---
            st.subheader(f"Aperçu des heures calculées - {mois_choisi}")
            
            # Ajouter une colonne pour indiquer les modifications
            display_df = adjusted_df.copy()
            display_df['Modifié'] = False
            for key in st.session_state.manual_adjustments.keys():
                emp_id, date_str = key.split('|')
                mask = (display_df['emp_id'] == emp_id) & (display_df['date'].dt.strftime('%Y-%m-%d') == date_str)
                display_df.loc[mask, 'Modifié'] = True
            
            st.dataframe(display_df[['emp_id', 'name', 'department', 'date', 'hours_worked', 'Role', 'Modifié']])
            
            # --- Préparation du CSV (avec données ajustées) ---
            csv = adjusted_df.to_csv(index=False)
            st.download_button(
                label=f"Télécharger le CSV - {mois_choisi}",
                data=csv,
                file_name=f"heures_journalieres_{mois_choisi.lower()}.csv",
                mime="text/csv"
            )
            
            # --- Résumé par employé (avec données ajustées) ---
            st.subheader(f"Résumé par employé - {mois_choisi}")
            resume = adjusted_df.groupby(['emp_id', 'name', 'department', 'Role'])['hours_worked'].agg(['sum', 'mean', 'count']).reset_index()
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
            
            # Bouton pour imprimer le statut des employés
            if st.button("🖨️ Imprimer les statuts des employés", key="print_status"):
                # Générer le contenu HTML à imprimer directement avec les données
                html_content = f"""
                <html>
                <head>
                    <title>Statut des Employés</title>
                    <style>
                        body {{ font-family: Arial, sans-serif; margin: 15px; }}
                        .header {{ text-align: center; margin-bottom: 20px; }}
                        .header h1 {{ font-size: 1.5em; margin: 10px 0; }}
                        .header p {{ font-size: 0.9em; margin: 5px 0; }}
                        .status-grid {{ 
                            display: grid; 
                            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); 
                            gap: 10px; 
                            max-height: 70vh;
                            overflow: hidden;
                        }}
                        .status-item {{ 
                            border: 2px solid; 
                            padding: 8px; 
                            border-radius: 6px; 
                            font-size: 0.85em;
                            margin-bottom: 0;
                        }}
                        .status-item p {{ margin: 3px 0; line-height: 1.2; }}
                        .legend {{ margin-top: 15px; text-align: center; }}
                        .legend-items {{ display: flex; justify-content: center; gap: 20px; font-weight: bold; font-size: 0.9em; }}
                        @media print {{ 
                            body {{ margin: 10px; font-size: 12px; }} 
                            .header h1 {{ font-size: 1.3em; }}
                            .status-grid {{ 
                                grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
                                gap: 8px;
                                page-break-inside: avoid;
                            }}
                            .status-item {{ 
                                padding: 6px; 
                                font-size: 0.8em;
                                break-inside: avoid;
                            }}
                            .legend {{ margin-top: 10px; }}
                        }}
                    </style>
                </head>
                <body>
                    <div class="header">
                        <h1>Statut des heures supplémentaires</h1>
                        <p>Généré le {datetime.now().strftime('%d/%m/%Y à %H:%M')} - Mois: {mois_choisi}</p>
                    </div>
                    <div class="status-grid">
                """
                
                # Ajouter chaque employé avec son statut
                for index, row in statut_df.iterrows():
                    statut = row['Statut']
                    couleurs = {
                        "Normal": "#4CAF50",
                        "Alerte": "#FFA500", 
                        "Dépassement": "#FF5733"
                    }
                    icones = {
                        "Normal": "🟢",
                        "Alerte": "🟠",
                        "Dépassement": "🔴"
                    }
                    
                    couleur = couleurs.get(statut, "#FFFFFF")
                    icone = icones.get(statut, "")
                    
                    html_content += f"""
                        <div class="status-item" style="border-color: {couleur};">
                            <p style="font-weight: bold; margin-bottom: 8px;">{icone} {row['Nom']}</p>
                            <p style="margin-bottom: 5px;">{row['Heures Totales']:.1f}h / {row['Seuil Individuel']:.1f}h</p>
                            <p style="margin-bottom: 0px;">{row['Heures Restantes']:.1f}h restantes</p>
                            <p style="margin-bottom: 0px; font-size: 0.9em; color: #666;">Rôle: {row['Role']}</p>
                        </div>
                    """
                
                html_content += """
                    </div>
                    <div class="legend">
                        <div class="legend-items">
                            <div>🟢 Normal</div>
                            <div>🟠 Proche du quota</div>
                            <div>🔴 Dépassement</div>
                        </div>
                    </div>
                    <script>
                        window.onload = function() {
                            setTimeout(function() {
                                window.print();
                            }, 100);
                        }
                    </script>
                </body>
                </html>
                """
                
                # Créer un bouton de téléchargement HTML pour l'impression
                st.download_button(
                    label="📄 Télécharger le rapport d'impression (HTML)",
                    data=html_content,
                    file_name=f"statut_employes_{mois_choisi.lower()}_{datetime.now().strftime('%Y%m%d')}.html",
                    mime="text/html"
                )
                
                # Alternative: utiliser JavaScript pour imprimer directement
                escaped_html = html_content.replace('`', '\\`')
                st.components.v1.html(f"""
                <script>
                    function printStatus() {{
                        var printWindow = window.open('', '_blank', 'width=800,height=600');
                        printWindow.document.write(`{escaped_html}`);
                        printWindow.document.close();
                        printWindow.focus();
                        setTimeout(function() {{
                            printWindow.print();
                        }}, 500);
                    }}
                    printStatus();
                </script>
                """, height=0)
            
            # --- Graphiques --- 
            st.subheader("Visualisations")
            tab1, tab2, tab3 = st.tabs(["Heures totales par employé", "Heures par département", "Tendance journalière"])
            
            # Utiliser la moyenne des seuils pour la ligne de référence globale des graphiques
            seuil_ref_graphiques = SEUIL_DEFAUT_MOYEN
            # Calcul d'une moyenne journalière indicative pour le graphique de tendance
            heures_jour_ref = seuil_ref_graphiques / 21 # Approximation avec 21 jours/mois
            
            with tab1:
                st.subheader(f"Heures totales travaillées par employé - {mois_choisi}")
                
                # Filtrer les données ajustées par rôle
                df_cuisine_adj = adjusted_df[adjusted_df['Role'] == 'Cuisine']
                df_salle_adj = adjusted_df[adjusted_df['Role'] == 'Salle']
                
                # Créer et afficher le graphique pour la Cuisine
                if not df_cuisine_adj.empty:
                    st.subheader("👨‍🍳 Employés Cuisine")
                    chart_cuisine = creer_graphique_heures_par_employe(df_cuisine_adj, SEUIL_MENSUEL_CUISINE, "Cuisine")
                    st.altair_chart(chart_cuisine, use_container_width=True)
                else:
                    st.info("Aucune donnée pour les employés de Cuisine ce mois-ci.")
                
                st.divider()
                
                # Créer et afficher le graphique pour la Salle
                if not df_salle_adj.empty:
                    st.subheader("💁 Employés Salle")
                    chart_salle = creer_graphique_heures_par_employe(df_salle_adj, SEUIL_MENSUEL_SALLE, "Salle")
                    st.altair_chart(chart_salle, use_container_width=True)
                else:
                    st.info("Aucune donnée pour les employés de Salle ce mois-ci.")
            
            with tab2:
                st.subheader(f"Heures travaillées par département - {mois_choisi}")
                # Passer la moyenne des seuils comme référence visuelle avec données ajustées
                chart1, chart_combo, pie = creer_graphiques_par_departement(adjusted_df, seuil_ref_graphiques)
                st.altair_chart(chart1, use_container_width=True)
                st.altair_chart(chart_combo, use_container_width=True)
                st.altair_chart(pie, use_container_width=True)
            
            with tab3:
                st.subheader(f"Tendance des heures travaillées par jour - {mois_choisi}")
                # Passer la moyenne journalière indicative comme référence avec données ajustées
                chart, heatmap = creer_graphiques_tendance_journaliere(adjusted_df, heures_jour_ref)
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
    6. **Modifiez manuellement les heures si nécessaire** (pour corriger les problèmes de pointeuse après minuit).
    7. L'application calculera les heures travaillées et le statut des heures supplémentaires basé sur le rôle et les seuils définis.
    8. Visualisez les résumés, statuts et graphiques (incluant les modifications manuelles).
    9. Téléchargez le résultat détaillé au format CSV.
    """) 