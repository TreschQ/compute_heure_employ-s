# Calcul des Heures Employés

Application Streamlit pour analyser les fichiers de pointage et calculer les heures travaillées par employé.

## Fonctionnalités

- Upload de fichiers Excel (.xls, .xlsx) de pointage
- Analyse automatique des horodatages
- Calcul des heures travaillées par employé et par jour
- Téléchargement des résultats au format CSV
- Résumé des heures totales par employé

## Installation

1. Clonez ce dépôt ou téléchargez les fichiers
2. Installez les dépendances:

```bash
pip install -r requirements.txt
```

## Lancement de l'application

```bash
streamlit run app.py
```

## Utilisation

1. Ouvrez l'application dans votre navigateur (généralement à l'adresse http://localhost:8501)
2. Téléchargez votre fichier Excel de pointage
3. Vérifiez ou modifiez le nom de l'onglet si nécessaire
4. L'application calculera automatiquement les heures travaillées
5. Téléchargez le résultat au format CSV

## Format de fichier attendu

L'application attend un fichier Excel avec:
- Une ligne contenant la période (format: YYYY/MM/DD ~ MM/DD)
- Une ligne d'en-tête contenant les jours du mois sous forme numérique
- Des blocs d'information par employé avec les champs "Non:", "Nom:", "Département:" 
- Les heures de pointage au format HH:MM dans les cellules correspondant aux jours travaillés

## Licence

Ce projet est distribué sous licence libre. 