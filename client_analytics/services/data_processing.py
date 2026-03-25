"""
Service de traitement des données - Reproduction exacte du notebook
Applique le même traitement que week_1_clean.ipynb sur Raw data High tech 2024.xlsx
"""

import pandas as pd
import numpy as np
import re
import matplotlib
matplotlib.use('Agg')  # Backend non-interactif pour serveur
import matplotlib.pyplot as plt
import seaborn as sns
import base64
from io import BytesIO

def process_raw_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Applique le traitement exact du notebook sur le fichier raw

    Étapes :
    1. Extraction du pays depuis Cpt Client
    2. Conversions de types + création Date_Ref (anti-NaT)
    3. Suppression de colonnes inutiles
    4. Suppression des doublons
    5. Filtrage des familles et clients
    6. Création des variables temporelles (trimestre fiscal Avril->Mars)
    7. Nettoyage des données
    8. Recalcul du PU Net
    9. Standardisation des devises (sans conversion)
    10. Création du dataset final

    Returns:
        df_final: DataFrame nettoyé avec devises originales et lead times
    """

    # ═══════════════════════════════════════════════════════════════════
    # ÉTAPE 1 : EXTRACTION DU PAYS DEPUIS CPT CLIENT
    # ═══════════════════════════════════════════════════════════════════

    country_mapping = {
        **{str(i).zfill(2): "FR" for i in range(0, 100)},  # 00-99 = France
        "AE": "AE", "AT": "AT", "AU": "AU", "BE": "BE", "BG": "BG", "BR": "BR",
        "CA": "CA", "CH": "CH", "CL": "CL", "CR": "CR", "CZ": "CZ", "DE": "DE",
        "DK": "DK", "ES": "ES", "GB": "GB", "GR": "GR", "HR": "HR", "HU": "HU",
        "IE": "IE", "IN": "IN", "IT": "IT", "LT": "LT", "LU": "LU", "MK": "MK",
        "NL": "NL", "NO": "NO", "PL": "PL", "PT": "PT", "RO": "RO", "RS": "RS",
        "SA": "SA", "SE": "SE", "SK": "SK", "UY": "UY",
    }

    def get_country_code(client_code):
        if pd.isna(client_code):
            return "Unknown"
        prefix = str(client_code)[:2]
        if prefix.isdigit():
            return "FR"
        return country_mapping.get(prefix, "Unknown")

    if "Cpt Client" in df.columns:
        df["Country"] = df["Cpt Client"].apply(get_country_code)
    else:
        df["Country"] = "Unknown"

    # ═══════════════════════════════════════════════════════════════════
    # ÉTAPE 2 : CONVERSIONS DE TYPES + Date_Ref
    # ═══════════════════════════════════════════════════════════════════

    # Parsing dates
    for col in ["Date Exp.", "Date Fact.", "Date Cde", "Delai Prev"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce", dayfirst=True)

    # Conversions numériques
    for col in ["Quantité", "Montant", "PU Net"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # ═══════════════════════════════════════════════════════════════════
    # ÉTAPE 3 : SUPPRESSION DE COLONNES
    # ═══════════════════════════════════════════════════════════════════

    cols_to_drop = ["Code Group", "Cpt Compta", "Cpte vente"]
    existing_cols_to_drop = [c for c in cols_to_drop if c in df.columns]
    if existing_cols_to_drop:
        df.drop(existing_cols_to_drop, axis=1, inplace=True)

    # Extraction code recette
    if "Code Artic" in df.columns:
        def extract_code(artic):
            if pd.isna(artic):
                return None
            matches = re.findall(r'([A-Z])(\d{3})', str(artic))
            if matches:
                chosen = matches[1] if len(matches) > 1 else matches[0]
                return chosen[0] + chosen[1]
            return None
        
        df['Code Recette'] = df['Code Artic'].apply(extract_code)
    else:
        df['Code Recette'] = None
    
    if "Date Cde" in df.columns:
        df.sort_values('Date Cde', inplace=True)

    if "Libelle 1" in df.columns and "Code Artic" in df.columns:
        df['Libelle 1'] = df.groupby('Code Artic')['Libelle 1'].transform('first')
    elif "Libelle 1" not in df.columns:
        df['Libelle 1'] = None

    # ═══════════════════════════════════════════════════════════════════
    # ÉTAPE 4 : SUPPRESSION DES DOUBLONS
    # ═══════════════════════════════════════════════════════════════════

    nb_avant = len(df)
    df = df.drop_duplicates()

    # ═══════════════════════════════════════════════════════════════════
    # ÉTAPE 5 : FILTRAGE DES FAMILLES ET CLIENTS
    # ═══════════════════════════════════════════════════════════════════

    nb_avant = len(df)

    if "Famille" in df.columns:
        familles_exclues = ["LIQ", "DEVL", "ZDIV", "POUD"]
        df = df[~df["Famille"].isin(familles_exclues)]

    if "Cpt Client" in df.columns:
        clients_exclus = ["13RLCA", "IENEWY"]
        df = df[~df["Cpt Client"].isin(clients_exclus)]

    # ═══════════════════════════════════════════════════════════════════
    # ÉTAPE 6 : VARIABLES TEMPORELLES (Fiscal Avril->Mars)
    # ═══════════════════════════════════════════════════════════════════

    # Filtrer les NaT avant set_index pour éviter les problèmes
    if "Date Fact." in df.columns:
        nb_nat = df["Date Fact."].isna().sum()
        if nb_nat > 0:
            df = df.dropna(subset=["Date Fact."])
        
        df.sort_values("Date Fact.", inplace=True)
        df.set_index("Date Fact.", drop=False, inplace=True)
        
        # Créer Date_Ref pour éviter les problèmes avec l'index datetime
        df["Date_Ref"] = df.index

        df["Year"] = df.index.year
        df["Month"] = df.index.to_period("M").astype(str)  # "YYYY-MM"

        # ✅ Trimestre fiscal Avril -> Mars
        df["Quarter"] = df.index.to_period("Q-MAR").astype(str)  # ex: "2025Q1"

        # ✅ Année fiscale (se termine en Mars)
        # Règle: si mois >= Avril (4), FY = année + 1, sinon FY = année
        df["Fiscal_Year"] = df.index.year + (df.index.month >= 4).astype(int)
        df["Fiscal_Year_Label"] = "FY" + df["Fiscal_Year"].astype(str)  # ex: "FY2025"
        
        # ✅ Label lisible pour le trimestre fiscal (ex: "Q1 FY2025 (Avr-Juin)")
        quarter_labels = {
            1: "Q1 (Avr-Juin)",
            2: "Q2 (Juil-Sep)",
            3: "Q3 (Oct-Déc)",
            4: "Q4 (Jan-Mar)"
        }
        df["Trimestre_Num"] = ((df.index.month - 4) % 12) // 3 + 1
        df["Fiscal_Quarter"] = df["Trimestre_Num"].map(quarter_labels) + " " + df["Fiscal_Year_Label"]

        df["Weekday"] = df.index.weekday
    else:
        df["Year"] = np.nan
        df["Month"] = None
        df["Quarter"] = None
        df["Fiscal_Year"] = np.nan
        df["Fiscal_Year_Label"] = None
        df["Trimestre_Num"] = np.nan
        df["Fiscal_Quarter"] = None
        df["Weekday"] = np.nan

    # Lead time
    if "Date Exp." in df.columns and "Date Cde" in df.columns:
        df["Lead_Time_Days"] = (df["Date Exp."] - df["Date Cde"]).dt.days
    else:
        df["Lead_Time_Days"] = np.nan

    if "Delai Prev" in df.columns and "Date Cde" in df.columns:
        df["Delai_Prev_Days"] = (df["Delai Prev"] - df["Date Cde"]).dt.days
    else:
        df["Delai_Prev_Days"] = np.nan

    df["Lead_Time_Deviation_Days"] = df["Lead_Time_Days"] - df["Delai_Prev_Days"]

    # ═══════════════════════════════════════════════════════════════════
    # ÉTAPE 7 : NETTOYAGE
    # ═══════════════════════════════════════════════════════════════════

    lignes_initiales = len(df)

    # sécurité : si colonnes absentes, on évite de crasher
    if "Quantité" in df.columns:
        df = df[df["Quantité"] != 0]
        df = df[df["Quantité"] >= 0]

    if "Montant" in df.columns:
        df = df[df["Montant"] != 0]
        df = df[df["Montant"] >= 0]

    # ═══════════════════════════════════════════════════════════════════
    # ÉTAPE 8 : RECALCUL PU NET
    # ═══════════════════════════════════════════════════════════════════

    if "Montant" in df.columns and "Quantité" in df.columns:
        df["PU Net"] = df["Montant"] / df["Quantité"]

    # ═══════════════════════════════════════════════════════════════════
    # ÉTAPE 10 : DATASET FINAL
    # ═══════════════════════════════════════════════════════════════════

    colonnes_finales = [
        # Dates & Temps
        "Date Fact.", "Date Cde", "Date Exp.", "Date_Ref",
        "Year", "Fiscal_Year", "Fiscal_Year_Label",
        "Month", "Quarter", "Weekday",
        "Trimestre_Num", "Fiscal_Quarter",

        # Client
        "Cpt Client", "Intitulé", "Country", "Code Recette",

        # Produit
        "Libelle 1", "Libelle 2", "Famille",

        # Financier
        "Montant", "PU Net", "Quantité", "Nom Devise",

        # Commande
        "N° Bon",

        # Délai (Lead Time)
        "Lead_Time_Days", "Delai_Prev_Days", "Lead_Time_Deviation_Days",
    ]

    colonnes_existantes = [c for c in colonnes_finales if c in df.columns]
    df_final = df[colonnes_existantes].copy()

    # AFFICHAGE DATAFRAME FINAL (seul print du module)
    print("\n" + "="*80)
    print("DATAFRAME FINAL APRÈS PROCESSING")
    print("="*80)
    print(df_final.head(10))
    print("="*80 + "\n")

    return df_final


def filter_data_by_period(df: pd.DataFrame, period_type: str = 'month', period_value=None) -> pd.DataFrame:
    """
    Filtre les données selon la période spécifiée
    
    Args:
        df: DataFrame avec colonnes Date_Ref, Fiscal_Year, Fiscal_Quarter, Month
        period_type: 'month', 'quarter', 'fiscal_year'
        period_value: Valeur de la période (ex: 'FY2024', 'Q1 (Avr-Juin) FY2025', '2024-01')
    
    Returns:
        DataFrame filtré
    """
    if period_value is None:
        return df.copy()
    
    df_filtered = df.copy()
    
    if period_type == 'month':
        # Filtrer par mois (format: 'YYYY-MM')
        if 'Month' in df_filtered.columns:
            df_filtered = df_filtered[df_filtered['Month'] == period_value]
        elif 'Date_Ref' in df_filtered.columns:
            df_filtered['_temp_month'] = pd.to_datetime(df_filtered['Date_Ref']).dt.to_period('M').astype(str)
            df_filtered = df_filtered[df_filtered['_temp_month'] == period_value]
            df_filtered = df_filtered.drop(columns=['_temp_month'])
    
    elif period_type == 'quarter':
        # Filtrer par trimestre fiscal (ex: 'Q1 (Avr-Juin) FY2025')
        if 'Fiscal_Quarter' in df_filtered.columns:
            df_filtered = df_filtered[df_filtered['Fiscal_Quarter'] == period_value]
        else:
            pass  # Colonne non trouvée
    
    elif period_type == 'fiscal_year':
        # Filtrer par année fiscale (ex: 'FY2024')
        if 'Fiscal_Year_Label' in df_filtered.columns:
            df_filtered = df_filtered[df_filtered['Fiscal_Year_Label'] == period_value]
    
    return df_filtered

def get_available_periods(df: pd.DataFrame) -> dict:
    """
    Récupère la liste des périodes disponibles dans les données
    
    Returns:
        dict avec 'months', 'quarters', 'fiscal_years'
    """
    periods = {
        'months': [],
        'quarters': [],
        'fiscal_years': []
    }
    
    # Mois disponibles
    if 'Month' in df.columns:
        periods['months'] = sorted(df['Month'].dropna().unique().tolist())
    elif 'Date_Ref' in df.columns:
        df_temp = df.copy()
        df_temp['YearMonth'] = pd.to_datetime(df_temp['Date_Ref']).dt.to_period('M').astype(str)
        periods['months'] = sorted(df_temp['YearMonth'].dropna().unique().tolist())
    
    # Trimestres fiscaux disponibles
    if 'Fiscal_Quarter' in df.columns:
        periods['quarters'] = sorted(df['Fiscal_Quarter'].dropna().unique().tolist())
    
    # Années fiscales disponibles
    if 'Fiscal_Year_Label' in df.columns:
        periods['fiscal_years'] = sorted(df['Fiscal_Year_Label'].dropna().unique().tolist())
    
    return periods
