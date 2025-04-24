import streamlit as st
import pandas as pd
import altair as alt

def creer_graphique_heures_par_employe(filtered_df, heures_standard):
    """
    Crée un graphique à barres montrant les heures totales par employé.
    """
    # Graphique Altair - Heures totales par employé avec ligne de référence
    heures_par_employe = filtered_df.groupby(['name'])['hours_worked'].sum().reset_index()
    heures_par_employe = heures_par_employe.sort_values('hours_worked', ascending=False)
    
    # Préparation des données
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
        dx=0,
        dy=-5,
        color='red',
        fontSize=14,
        fontWeight='bold'
    ).encode(
        y='threshold:Q',
        text=alt.value(f"Seuil: {heures_standard}h")
    )
    
    # Barre pour heures totales
    bars = alt.Chart(heures_par_employe).mark_bar().encode(
        x=alt.X('name:N', title='Employé', sort='-y', axis=alt.Axis(labelAngle=-45)),
        y=alt.Y('hours_worked:Q', title='Heures totales'),
        color=alt.condition(
            alt.datum.hours_worked > heures_standard,
            alt.value('#FF5733'),  # rouge pour heures supp
            alt.value('#4CAF50')   # vert pour heures normales
        ),
        tooltip=['name', alt.Tooltip('hours_worked:Q', title='Heures totales')]
    )
    
    # Combinaison des graphiques
    chart = (bars + rule + text).properties(
        height=400,
        title=f"Heures travaillées (seuil: {heures_standard}h)"
    ).interactive()
    
    return chart

def creer_graphiques_par_departement(filtered_df, heures_standard):
    """
    Crée des graphiques montrant les heures par département.
    """
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
    
    # Création du heatmap
    heatmap = alt.Chart(heatmap_data).mark_rect().encode(
        x=alt.X('jour:N', title='Jour', sort=None),
        y=alt.Y('name:N', title='Employé'),
        color=alt.Color('hours_worked:Q', scale=alt.Scale(scheme='blues'), 
                        legend=alt.Legend(title="Heures")),
        tooltip=['name', 'jour', 'hours_worked']
    ).properties(
        title="Heures travaillées par jour et par employé",
        height=len(heatmap_data['name'].unique()) * 30 + 50
    )
    
    # Ajout des valeurs dans les cellules
    text_heatmap = alt.Chart(heatmap_data).mark_text(color='black').encode(
        x=alt.X('jour:N'),
        y=alt.Y('name:N'),
        text=alt.Text('hours_worked:Q', format='.1f')
    )
    
    return chart, heatmap + text_heatmap

def afficher_statut_employes(statut_df, heures_standard):
    """
    Affiche le statut des heures supplémentaires pour chaque employé.
    """
    # Nombre d'employés à afficher par ligne
    employes_par_ligne = 3
    
    # Calculer le nombre de lignes nécessaires
    nb_employes = len(statut_df)
    nb_lignes = (nb_employes + employes_par_ligne - 1) // employes_par_ligne
    
    # Créer des groupes d'employés pour l'affichage
    for i in range(nb_lignes):
        # Créer une ligne avec 3 colonnes
        cols = st.columns(employes_par_ligne)
        
        # Afficher jusqu'à 3 employés par ligne
        for j in range(employes_par_ligne):
            idx = i * employes_par_ligne + j
            if idx < nb_employes:
                employe = statut_df.iloc[idx]
                with cols[j]:
                    # Définir le style visuel en fonction du statut
                    if employe['Statut'] == "Dépassement":
                        color = "#FF5733"  # Rouge
                        emoji = "🔴"
                        message = f"+{employe['Heures Supp']:.1f}h supp."
                    elif employe['Statut'] == "Alerte":
                        color = "#FFC300"  # Orange/Jaune
                        emoji = "🟠"
                        message = f"{employe['Heures Restantes']:.1f}h restantes"
                    else:
                        color = "#4CAF50"  # Vert
                        emoji = "🟢" 
                        message = f"{employe['Heures Restantes']:.1f}h restantes"
                    
                    # Créer le conteneur avec un style personnalisé
                    with st.container():
                        st.markdown(f"""
                        <div style="
                            padding: 10px; 
                            border-radius: 5px; 
                            border: 2px solid {color}; 
                            background-color: rgba({int(color[1:3], 16)}, {int(color[3:5], 16)}, {int(color[5:7], 16)}, 0.1);
                            text-align: center;
                            margin-bottom: 10px;
                        ">
                            <h3 style="margin:0; font-size: 1.2em;">{emoji} {employe['Nom']}</h3>
                            <p style="margin:0; font-weight: bold;">{employe['Heures Totales']:.1f}h / {heures_standard}h</p>
                            <p style="margin:0; color: {color};">{message}</p>
                        </div>
                        """, unsafe_allow_html=True)
    
    # Légende
    st.markdown("""
    <div style="display: flex; justify-content: center; gap: 20px; margin-top: 15px;">
        <div>🟢 Normal</div>
        <div>🟠 Proche du quota</div>
        <div>🔴 Dépassement</div>
    </div>
    """, unsafe_allow_html=True) 