import streamlit as st
import pandas as pd
import re
from datetime import datetime, timedelta
import io
import altair as alt
import calendar

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

def lire_onglet_excel(file, nom_onglet):
    """
    Ouvre le fichier Excel et renvoie le DataFrame de l'onglet choisi.
    """
    df = pd.read_excel(file, sheet_name=nom_onglet)
    return df

def traiter_fichier(file, nom_onglet):
    # 1) Lecture brute, tout en str
    df = lire_onglet_excel(file, nom_onglet)
    df = df.fillna("").astype(str)

    # 2) Repérer la période (YYYY/MM/DD ~ MM/DD)
    period_text = ""
    for cell in df.values.flatten():
        if isinstance(cell, str) and re.search(r"\d{4}/\d{2}/\d{2}\s*~", cell):
            period_text = cell
            break
    if not period_text:
        raise ValueError("Période non trouvée dans le fichier.")

    m = re.search(r"(\d{4})/(\d{2})/(\d{2})\s*~\s*(\d{2})/(\d{2})", period_text)
    year, month = m.group(1), m.group(2)
    ym_prefix = f"{year}-{month}"

    # 3) Détection de la première "ligne des jours"
    num_pat = re.compile(r"^\d+(\.\d+)?$")
    header_idx = None
    for idx, row in df.iterrows():
        # on regarde les cellules à partir de la 2ᵉ colonne (col index 1)
        cells = [c.strip() for c in row.tolist()[1:]]
        num_count = sum(bool(num_pat.match(c)) for c in cells)
        if num_count >= 10:  # typiquement 21 valeurs numériques
            header_idx = idx
            break
    if header_idx is None:
        raise ValueError("Ligne des jours introuvable")

    # 4) Construire le mapping col→jour
    day_by_col = {}
    for col, val in df.iloc[header_idx].items():
        v = str(val).strip()
        if num_pat.match(v):
            day_by_col[col] = int(float(v))

    # 5) On travaille à partir de la ligne juste après
    sub = df.iloc[header_idx + 1 :].reset_index(drop=True)

    records = []
    i = 0
    while i < len(sub):
        row = sub.iloc[i]
        tokens = [c.strip() for c in row.tolist()]
        # Repérer un bloc "Non :"
        non_pos = next((j for j, t in enumerate(tokens) if t.startswith("Non")), None)
        if non_pos is not None:
            # extraire emp_id, name, dept (on prend la 3ᵉ cellule après le label)
            emp_id = tokens[non_pos + 2] if len(tokens) > non_pos + 2 else ""
            # Nom
            nom_pos = next((j for j, t in enumerate(tokens) if t.startswith("Nom")), None)
            name = tokens[nom_pos + 2] if nom_pos is not None and len(tokens) > nom_pos + 2 else ""
            # Département
            dep_pos = next((j for j, t in enumerate(tokens) if t.startswith("Département")), None)
            dept = tokens[dep_pos + 2] if dep_pos is not None and len(tokens) > dep_pos + 2 else ""
            # Ligne suivante = pointages
            if i + 1 < len(sub):
                times_row = sub.iloc[i + 1]
                for col, day in day_by_col.items():
                    cell = str(times_row[col]).strip()
                    if not cell:
                        continue
                    # plusieurs tampons séparés par saut de ligne
                    stamps = [t.strip() for t in cell.splitlines() if t.strip()]
                    # parser en datetime
                    times = []
                    for t in stamps:
                        try:
                            times.append(datetime.strptime(t, "%H:%M"))
                        except:
                            pass
                    # si impair, on retire le dernier
                    if len(times) % 2 == 1:
                        times = times[:-1]
                    # sommer les intervalles (entrée–sortie)
                    total = timedelta()
                    for k in range(0, len(times), 2):
                        start, end = times[k], times[k + 1]
                        if end < start:  # passage minuit
                            end += timedelta(days=1)
                        total += (end - start)
                    hours = total.total_seconds() / 3600
                    date_str = f"{ym_prefix}-{day:02d}"
                    records.append({
                        "emp_id": emp_id,
                        "name":   name,
                        "department": dept,
                        "date":   date_str,
                        "hours_worked": round(hours, 2)
                    })
            i += 2  # on saute la ligne Non: … et la ligne des horaires
        else:
            i += 1

    # 6) Finalisation
    res = pd.DataFrame(records)
    if not res.empty:
        res = res.sort_values(["emp_id", "date"]).reset_index(drop=True)
    return res

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
            def determiner_statut(heures_totales, heures_standard, marge_alerte):
                if heures_totales > heures_standard:
                    return "Dépassement"
                elif heures_standard - heures_totales <= marge_alerte:
                    return "Alerte"
                else:
                    return "Normal"
                
            resume['Statut'] = resume.apply(
                lambda x: determiner_statut(x['Heures Totales'], heures_standard, marge_alerte), 
                axis=1
            )
            
            # Affichage des statuts d'heures supp dans un tableau visuel
            st.subheader("Statut des heures supplémentaires")
            
            # Création d'un tableau visuel avec des indicateurs colorés
            statut_df = resume.sort_values('Heures Totales', ascending=False)
            
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
            
            # Graphiques
            st.subheader("Visualisations")
            
            # Conversion pour Altair
            heures_standard_str = str(heures_standard)
            heures_jour_str = str(heures_jour)
            
            # Onglets pour différentes visualisations
            tab1, tab2, tab3 = st.tabs(["Heures totales par employé", "Heures par département", "Tendance journalière"])
            
            with tab1:
                st.subheader(f"Heures totales travaillées par employé - {mois_choisi}")
                
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
                
                st.altair_chart(chart, use_container_width=True)
            
            with tab2:
                st.subheader(f"Heures travaillées par département - {mois_choisi}")
                
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
                
                st.altair_chart(chart1, use_container_width=True)
                
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
                
                st.altair_chart(chart_combo, use_container_width=True)
                
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
                
                st.altair_chart(pie, use_container_width=True)
            
            with tab3:
                st.subheader(f"Tendance des heures travaillées par jour - {mois_choisi}")
                
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
                
                st.altair_chart(chart, use_container_width=True)
                
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
                
                st.altair_chart(heatmap + text_heatmap, use_container_width=True)
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