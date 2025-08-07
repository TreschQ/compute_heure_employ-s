import streamlit as st
import pandas as pd
import altair as alt

def creer_graphique_heures_par_employe(df_role_specific, seuil_role_specific, role_name):
    """
    Crée un graphique à barres montrant les heures totales par employé 
    pour un rôle spécifique (Salle ou Cuisine) avec le seuil correspondant.

    Args:
        df_role_specific (pd.DataFrame): DataFrame filtré pour un seul rôle.
        seuil_role_specific (float): Seuil mensuel d'heures pour ce rôle.
        role_name (str): Nom du rôle ("Salle" ou "Cuisine") pour le titre.
    """
    if df_role_specific.empty:
        # Retourner un graphique vide ou un message si aucune donnée pour ce rôle
        return alt.Chart().mark_text(text=f"Aucun employé trouvé pour le rôle {role_name}.").properties(height=100)

    # Graphique Altair - Heures totales par employé avec ligne de référence spécifique
    heures_par_employe = df_role_specific.groupby(['name'])['hours_worked'].sum().reset_index()
    heures_par_employe = heures_par_employe.sort_values('hours_worked', ascending=False)
    
    # Préparation des données pour la ligne de référence spécifique
    heures_ref_df = pd.DataFrame([{'threshold': seuil_role_specific}])
    
    # Ligne de référence pour heures standard du rôle
    rule = alt.Chart(heures_ref_df).mark_rule(
        strokeDash=[12, 6],
        stroke='red',
        strokeWidth=2
    ).encode(
        y='threshold:Q'
    )
    
    # Texte pour la ligne de référence
    text = alt.Chart(heures_ref_df).mark_text(
        align='right',
        baseline='bottom',
        dx=0,
        dy=-5,
        color='red',
        fontSize=14,
        fontWeight='bold'
    ).encode(
        y='threshold:Q',
        text=alt.value(f"Seuil {role_name}: {seuil_role_specific:.2f}h")
    )
    
    # Barre pour heures totales
    bars = alt.Chart(heures_par_employe).mark_bar().encode(
        x=alt.X('name:N', title='Employé', sort='-y', axis=alt.Axis(labelAngle=-45)),
        y=alt.Y('hours_worked:Q', title='Heures totales'),
        color=alt.condition(
            alt.datum.hours_worked > seuil_role_specific,
            alt.value('#FF5733'),  # rouge pour heures supp
            alt.value('#4CAF50')   # vert pour heures normales
        ),
        tooltip=['name', alt.Tooltip('hours_worked:Q', title='Heures totales')]
    )
    
    # Combinaison des graphiques
    chart = (bars + rule + text).properties(
        height=400,
        title=f"Heures travaillées ({role_name} - Seuil: {seuil_role_specific:.2f}h)"
    ).interactive()
    
    return chart

def creer_graphiques_par_departement(filtered_df, heures_standard):
    """
    Crée des graphiques montrant les heures par département.
    """
    # Vérifier si le DataFrame est vide
    if filtered_df.empty:
        empty_chart = alt.Chart().mark_text(text="Aucune donnée disponible").properties(height=100)
        return empty_chart, empty_chart, empty_chart
    
    # Graphique des heures par département
    heures_par_dept = filtered_df.groupby(['department'])['hours_worked'].sum().reset_index()
    heures_par_dept = heures_par_dept.sort_values('hours_worked', ascending=False)
    
    # Calcul des heures moyennes par employé dans chaque département
    dept_emp_count = filtered_df.groupby('department')['name'].nunique().reset_index()
    dept_emp_count.columns = ['department', 'nombre_employes']
    
    heures_par_dept = heures_par_dept.merge(dept_emp_count, on='department')
    heures_par_dept['heures_moyennes_par_employe'] = heures_par_dept['hours_worked'] / heures_par_dept['nombre_employes']
    
    # Graphique des heures totales par département
    chart1 = alt.Chart(heures_par_dept).mark_bar().encode(
        x=alt.X('department:N', title='Département', sort='-y'),
        y=alt.Y('hours_worked:Q', title='Heures totales'),
        color=alt.Color('department:N', legend=None),
        tooltip=['department', 'hours_worked', 'nombre_employes', 
                 alt.Tooltip('heures_moyennes_par_employe:Q', title='Moyenne par employé')]
    ).properties(
        height=400,
        title="Heures totales par département"
    ).interactive()
    
    # Graphique des heures moyennes par employé dans chaque département
    chart2 = alt.Chart(heures_par_dept).mark_bar().encode(
        x=alt.X('department:N', title='Département', sort='-y'),
        y=alt.Y('heures_moyennes_par_employe:Q', title='Heures moyennes par employé'),
        color=alt.Color('department:N', legend=None),
        tooltip=['department', 'nombre_employes', 
                 alt.Tooltip('heures_moyennes_par_employe:Q', title='Moyenne par employé')]
    )
    
    # Préparation des données pour la ligne de référence
    heures_ref_df = pd.DataFrame([{'threshold': heures_standard}])
    
    # Ligne de référence pour heures standard
    rule = alt.Chart(heures_ref_df).mark_rule(
        strokeDash=[12, 6],
        stroke='red',
        strokeWidth=2
    ).encode(
        y='threshold:Q'
    )
    
    # Texte pour la ligne de référence
    text = alt.Chart(heures_ref_df).mark_text(
        align='right',
        baseline='top',
        dx=-5,
        dy=-5,
        color='red',
        fontSize=14,
        fontWeight='bold'
    ).encode(
        y='threshold:Q',
        text=alt.value(f"Seuil: {heures_standard}h")
    )
    
    chart_combo = (chart2 + rule + text).properties(
        height=400,
        title="Heures moyennes par employé dans chaque département"
    ).interactive()
    
    # Graphique circulaire avec Altair
    pie_data = heures_par_dept.copy()
    if len(pie_data) == 0 or pie_data['hours_worked'].sum() == 0:
        pie = alt.Chart().mark_text(text="Aucune donnée pour le graphique circulaire").properties(height=100)
    else:
        pie_data['angle'] = pie_data['hours_worked'] / pie_data['hours_worked'].sum() * 2 * 3.14159
        pie_data['percentage'] = (pie_data['hours_worked'] / pie_data['hours_worked'].sum() * 100).round(1).astype(str) + '%'
    
        pie = alt.Chart(pie_data).mark_arc().encode(
            theta='angle:Q',
            color=alt.Color('department:N', scale=alt.Scale(scheme='category10')),
            tooltip=['department', 'hours_worked', 'percentage']
        ).properties(
            title="Répartition des heures par département",
            height=400
        )
        
        # Ajout des labels au graphique
        text = alt.Chart(pie_data).mark_text(radiusOffset=20).encode(
            theta=alt.value(0),
            radius=alt.value(100),
            text='department:N',
            color=alt.value('black')
        )
    
    return chart1, chart_combo, pie

def creer_graphiques_tendance_journaliere(filtered_df, heures_jour):
    """
    Crée des graphiques montrant la tendance des heures par jour.
    """
    # Vérifier si le DataFrame est vide
    if filtered_df.empty:
        empty_chart = alt.Chart().mark_text(text="Aucune donnée disponible").properties(height=100)
        return empty_chart, empty_chart
    
    # Préparation des données pour la tendance journalière
    heures_par_jour = filtered_df.groupby('date')['hours_worked'].sum().reset_index()
    
    # Préparation des données pour la ligne de référence
    heures_ref_df = pd.DataFrame([{'threshold': heures_jour}])
    
    # Graphique Altair pour la tendance journalière avec ligne de référence
    line = alt.Chart(heures_par_jour).mark_line(
        point=alt.OverlayMarkDef(color="blue", size=60),
        color="blue",
        strokeWidth=3
    ).encode(
        x=alt.X('date:T', title='Date', axis=alt.Axis(format='%d/%m', labelAngle=-45)),
        y=alt.Y('hours_worked:Q', title='Heures totales'),
        tooltip=[
            alt.Tooltip('date:T', title='Date', format='%d/%m/%Y'),
            alt.Tooltip('hours_worked:Q', title='Heures totales')
        ]
    )
    
    # Ajout d'une coloration pour les heures supplémentaires
    heures_par_jour['est_supp'] = heures_par_jour['hours_worked'] > heures_jour
    
    # Créer un dataframe pour les zones dépassant le seuil
    supp_data = []
    for _, row in heures_par_jour.iterrows():
        if row['hours_worked'] > heures_jour:
            supp_data.append({
                'date': row['date'],
                'hours_worked': row['hours_worked'],
                'threshold': heures_jour
            })
    
    if supp_data:
        supp_df = pd.DataFrame(supp_data)
        
        # Ajout d'une bande pour indiquer le dépassement du seuil
        area = alt.Chart(supp_df).mark_area(
            color='rgba(255, 0, 0, 0.2)',
            opacity=0.5
        ).encode(
            x='date:T',
            y=alt.Y('hours_worked:Q'),
            y2=alt.Y2('threshold:Q')
        )
    else:
        area = alt.Chart().mark_area()  # Graphique vide
    
    # Ligne de référence pour heures par jour standard
    rule = alt.Chart(heures_ref_df).mark_rule(
        strokeDash=[12, 6],
        stroke='red',
        strokeWidth=2
    ).encode(
        y='threshold:Q'
    )
    
    # Texte pour la ligne de référence
    text = alt.Chart(heures_ref_df).mark_text(
        align='right',
        baseline='bottom',
        dx=-5,
        dy=5,
        color='red',
        fontSize=14,
        fontWeight='bold'
    ).encode(
        y='threshold:Q',
        text=alt.value(f"Seuil quotidien: {heures_jour:.2f}h")
    )
    
    # Combinaison des graphiques
    chart = (line + area + rule + text).properties(
        height=400,
        title="Évolution des heures travaillées"
    ).interactive()
    
    # Heatmap des heures par jour par employé avec Altair
    # Préparation des données
    heatmap_data = filtered_df.copy()
    heatmap_data['jour'] = heatmap_data['date'].dt.strftime('%d/%m')
    
    # Création du heatmap avec coloration spéciale pour les valeurs > 12h
    heatmap = alt.Chart(heatmap_data).mark_rect().encode(
        x=alt.X('jour:N', title='Jour', sort=None),
        y=alt.Y('name:N', title='Employé'),
        color=alt.condition(
            alt.datum.hours_worked > 12,
            alt.value('#FF5733'),  # rouge pour > 12h
            alt.Color('hours_worked:Q', scale=alt.Scale(scheme='blues'), 
                     legend=alt.Legend(title="Heures"))
        ),
        tooltip=['name', 'jour', 'hours_worked']
    ).properties(
        title="Heures travaillées par jour et par employé (>12h en rouge)",
        height=len(heatmap_data['name'].unique()) * 30 + 50
    )
    
    # Ajout des valeurs dans les cellules
    text_heatmap = alt.Chart(heatmap_data).mark_text(color='black').encode(
        x=alt.X('jour:N'),
        y=alt.Y('name:N'),
        text=alt.Text('hours_worked:Q', format='.1f')
    )
    
    return chart, heatmap + text_heatmap

def afficher_statut_employes(statut_df):
    """
    Affiche le statut des heures (Normal, Alerte, Dépassement) pour chaque employé 
    en utilisant les données pré-calculées dans le DataFrame.

    Args:
        statut_df (pd.DataFrame): DataFrame contenant au moins les colonnes
                                  'Nom', 'Heures Totales', 'Seuil Individuel',
                                  'Heures Restantes', 'Statut'.
    """
    # Vérifier la présence des colonnes nécessaires
    required_cols = ['Nom', 'Heures Totales', 'Seuil Individuel', 'Heures Restantes', 'Statut']
    if not all(col in statut_df.columns for col in required_cols):
        st.error(f"Le DataFrame doit contenir les colonnes: {required_cols}")
        return

    # Définir les couleurs par statut
    couleurs = {
        "Normal": "#4CAF50",  # Vert
        "Alerte": "#FFA500",  # Orange
        "Dépassement": "#FF5733" # Rouge
    }
    icones = {
        "Normal": "🟢",
        "Alerte": "🟠",
        "Dépassement": "🔴"
    }

    # Afficher les statuts pour chaque employé
    cols = st.columns(3) # Affichage sur 3 colonnes
    col_idx = 0
    for index, row in statut_df.iterrows():
        with cols[col_idx % 3]:
            statut = row['Statut']
            couleur = couleurs.get(statut, "#FFFFFF") # Blanc par défaut
            icone = icones.get(statut, "")
            
            # Utiliser les colonnes pré-calculées du DataFrame
            heures_travaillees = row['Heures Totales']
            seuil_employe = row['Seuil Individuel']
            heures_restantes = row['Heures Restantes'] # Déjà calculé correctement
            
            # Style CSS pour la bordure colorée
            st.markdown(
                f"""<div style='border: 2px solid {couleur}; 
                                    padding: 10px; 
                                    border-radius: 5px; 
                                    margin-bottom: 10px;'>
                        <p style='font-weight: bold; margin-bottom: 5px;'>{icone} {row['Nom']}</p>
                        <p style='margin-bottom: 3px;'>{heures_travaillees:.1f}h / {seuil_employe:.2f}h</p>
                        <p style='margin-bottom: 0px;'>{heures_restantes:.1f}h restantes</p>
                    </div>""",
                unsafe_allow_html=True
            )
        col_idx += 1

    # Légende
    st.markdown("""
    <div style="display: flex; justify-content: center; gap: 20px; margin-top: 15px;">
        <div>🟢 Normal</div>
        <div>🟠 Proche du quota</div>
        <div>🔴 Dépassement</div>
    </div>
    """, unsafe_allow_html=True) 