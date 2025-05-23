import pandas as pd
import re
from datetime import datetime, timedelta

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

def determiner_statut(heures_totales, seuil_heures_standard, marge_alerte):
    """Détermine le statut en fonction des heures travaillées par rapport au seuil spécifique."""
    if heures_totales > seuil_heures_standard:
        return "Dépassement"
    elif seuil_heures_standard - heures_totales <= marge_alerte:
        return "Alerte"
    else:
        return "Normal" 