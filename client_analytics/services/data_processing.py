"""
Service de traitement des données - Reproduction exacte du notebook
Applique le même traitement que week_1_clean.ipynb sur Raw data High tech 2024.xlsx
"""
import pandas as pd
import numpy as np
import re


def process_raw_data(df):
    """
    Applique le traitement exact du notebook sur le fichier raw
    
    Étapes :
    1. Extraction du pays depuis Cpt Client
    2. Conversions de types
    3. Suppression de colonnes inutiles
    4. Extraction du Code Recette
    5. Suppression des doublons
    6. Filtrage des familles et clients
    7. Création des variables temporelles
    8. Nettoyage des données
    9. Recalcul du PU Net
    10. Conversion des devises
    11. Création du dataset final
    
    Args:
        df: DataFrame brut (35644 lignes, 22 colonnes)
    
    Returns:
        df_final: DataFrame nettoyé (22796 lignes, 20 colonnes)
    """
    
    print("🔄 Début du traitement des données (identique au notebook)...")
    print(f"   📊 Données initiales : {len(df):,} lignes × {len(df.columns)} colonnes")
    
    # ═══════════════════════════════════════════════════════════════════
    # ÉTAPE 1 : EXTRACTION DU PAYS DEPUIS CPT CLIENT
    # ═══════════════════════════════════════════════════════════════════
    
    print("\n   🌍 Étape 1 : Extraction du pays...")
    
    country_mapping = {
        **{str(i).zfill(2): 'FR' for i in range(0, 100)},  # 00-99 = France
        'AE': 'AE', 'AT': 'AT', 'AU': 'AU', 'BE': 'BE', 'BG': 'BG', 'BR': 'BR',
        'CA': 'CA', 'CH': 'CH', 'CL': 'CL', 'CR': 'CR', 'CZ': 'CZ', 'DE': 'DE',
        'DK': 'DK', 'ES': 'ES', 'GB': 'GB', 'GR': 'GR', 'HR': 'HR', 'HU': 'HU',
        'IE': 'IE', 'IN': 'IN', 'IT': 'IT', 'LT': 'LT', 'LU': 'LU', 'MK': 'MK',
        'NL': 'NL', 'NO': 'NO', 'PL': 'PL', 'PT': 'PT', 'RO': 'RO', 'RS': 'RS',
        'SA': 'SA', 'SE': 'SE', 'SK': 'SK', 'UY': 'UY'
    }
    
    def get_country_code(client_code):
        if pd.isna(client_code):
            return 'Unknown'
        prefix = str(client_code)[:2]
        if prefix.isdigit():
            return 'FR'
        return country_mapping.get(prefix, 'Unknown')
    
    df['Country'] = df['Cpt Client'].apply(get_country_code)
    print(f"      ✅ Pays extraits : {df['Country'].nunique()} pays uniques")
    
    # ═══════════════════════════════════════════════════════════════════
    # ÉTAPE 2 : CONVERSIONS DE TYPES
    # ═══════════════════════════════════════════════════════════════════
    
    print("\n   🔧 Étape 2 : Conversions de types...")
    
    df['Date Exp.'] = pd.to_datetime(df['Date Exp.'], errors='coerce')
    df['Date Fact.'] = pd.to_datetime(df['Date Fact.'], errors='coerce')
    df['Date Cde'] = pd.to_datetime(df['Date Cde'], errors='coerce')
    df['Delai Prev'] = pd.to_datetime(df['Delai Prev'], errors='coerce')
    
    df['Quantité'] = df['Quantité'].astype(float)
    df['Montant'] = df['Montant'].astype(float)
    df['PU Net'] = df['PU Net'].astype(float)
    
    print(f"      ✅ Conversions terminées")
    
    # ═══════════════════════════════════════════════════════════════════
    # ÉTAPE 3 : SUPPRESSION DE COLONNES
    # ═══════════════════════════════════════════════════════════════════
    
    print("\n   🗑️ Étape 3 : Suppression de colonnes inutiles...")
    
    cols_to_drop = ['Code Group', 'Cpt Compta', 'Cpte vente']
    existing_cols_to_drop = [col for col in cols_to_drop if col in df.columns]
    if existing_cols_to_drop:
        df.drop(existing_cols_to_drop, axis=1, inplace=True)
        print(f"      ✅ Colonnes supprimées : {existing_cols_to_drop}")
    
    # Uniformiser Libelle 1
    if 'Code Artic' in df.columns and 'Libelle 1' in df.columns:
        df['Libelle 1'] = df.groupby('Code Artic')['Libelle 1'].transform('first')
    
    # ═══════════════════════════════════════════════════════════════════
    # ÉTAPE 4 : EXTRACTION DU CODE RECETTE
    # ═══════════════════════════════════════════════════════════════════
    
    print("\n   📝 Étape 4 : Extraction du Code Recette...")
    
    def extract_code(artic):
        if pd.isna(artic):
            return None
        matches = re.findall(r'([A-Z])(\\d{3})', str(artic))
        if matches:
            chosen = matches[1] if len(matches) > 1 else matches[0]
            return chosen[0] + chosen[1]
        return None
    
    if 'Code Artic' in df.columns:
        df['Code Recette'] = df['Code Artic'].apply(extract_code)
        print(f"      ✅ Code Recette extrait")
    
    # ═══════════════════════════════════════════════════════════════════
    # ÉTAPE 5 : SUPPRESSION DES DOUBLONS
    # ═══════════════════════════════════════════════════════════════════
    
    print("\n   🔍 Étape 5 : Suppression des doublons...")
    
    nb_avant = len(df)
    df = df.drop_duplicates()
    nb_doublons = nb_avant - len(df)
    print(f"      ❌ Supprimé {nb_doublons:,} doublons")
    
    # ═══════════════════════════════════════════════════════════════════
    # ÉTAPE 6 : FILTRAGE DES FAMILLES ET CLIENTS
    # ═══════════════════════════════════════════════════════════════════
    
    print("\n   🎯 Étape 6 : Filtrage des familles et clients...")
    
    nb_avant = len(df)
    
    # Supprimer certaines familles
    if 'Famille' in df.columns:
        familles_exclues = ['LIQ', 'DEVL', 'ZDIV', 'POUD']
        df = df[~df['Famille'].isin(familles_exclues)]
        print(f"      ❌ Familles exclues : {familles_exclues}")
    
    # Supprimer certains clients (outliers délais)
    if 'Cpt Client' in df.columns:
        clients_exclus = ['13RLCA', 'IENEWY']
        df = df[~df['Cpt Client'].isin(clients_exclus)]
        print(f"      ❌ Clients exclus : {clients_exclus}")
    
    nb_filtres = nb_avant - len(df)
    print(f"      ✅ Total filtré : {nb_filtres:,} lignes")
    
    # ═══════════════════════════════════════════════════════════════════
    # ÉTAPE 7 : CRÉATION DES VARIABLES TEMPORELLES
    # ═══════════════════════════════════════════════════════════════════
    
    print("\n   📅 Étape 7 : Création des variables temporelles...")
    
    # Index sur Date Exp.
    df.set_index('Date Exp.', inplace=True)
    df.sort_index(inplace=True)
    
    # Variables temporelles depuis l'index
    df['Year'] = df.index.year
    df['Month'] = df.index.to_period('M')
    df['Quarter'] = df.index.to_period('Q')
    df['Weekday'] = df.index.weekday
    df['Day'] = df.index.day
    
    # Calculs de délais
    df['Delay_Exp'] = (df.index - df['Date Cde']).dt.days
    df['Delay_Fact'] = (df['Date Fact.'] - df['Date Cde']).dt.days
    df['Delai_Prev_Days'] = (df['Delai Prev'] - df['Date Cde']).dt.days
    df['Delay_Deviation'] = df['Delay_Exp'] - df['Delai_Prev_Days']
    
    # Ventes cumulatives et rolling
    df['Cumulative_Sales_Client'] = df.groupby('Cpt Client')['Montant'].cumsum()
    df['Rolling_3M_Sales'] = df['Montant'].rolling('90D').sum()
    
    print(f"      ✅ Variables temporelles créées")
    
    # ═══════════════════════════════════════════════════════════════════
    # ÉTAPE 8 : NETTOYAGE DES DONNÉES
    # ═══════════════════════════════════════════════════════════════════
    
    print("\n   🧹 Étape 8 : Nettoyage des données...")
    
    lignes_initiales = len(df)
    print(f"      📊 Lignes avant nettoyage : {lignes_initiales:,}")
    
    # Supprimer Quantité = 0
    qty_zero = (df['Quantité'] == 0).sum()
    df = df[df['Quantité'] != 0]
    print(f"      ❌ Supprimé {qty_zero:,} lignes avec Quantité = 0")
    
    # Supprimer Montant = 0
    montant_zero = (df['Montant'] == 0).sum()
    df = df[df['Montant'] != 0]
    print(f"      ❌ Supprimé {montant_zero:,} lignes avec Montant = 0")
    
    # Supprimer Quantité négative
    qty_negative = (df['Quantité'] < 0).sum()
    df = df[df['Quantité'] >= 0]
    print(f"      ❌ Supprimé {qty_negative:,} lignes avec Quantité négative")
    
    # Supprimer Montant négatif
    montant_negative = (df['Montant'] < 0).sum()
    df = df[df['Montant'] >= 0]
    print(f"      ❌ Supprimé {montant_negative:,} lignes avec Montant négatif")
    
    # Filtrer sur 2024 uniquement
    df = df[df['Date Cde'].dt.year == 2024].copy()
    
    # Recalculer Quarter depuis Date Cde
    df["Quarter"] = df["Date Cde"].dt.to_period("Q").astype(str)
    
    trimestres = sorted(df["Quarter"].unique())
    print(f"      ✅ Trimestres 2024 : {trimestres}")
    print(f"      📊 Lignes après nettoyage : {len(df):,}")
    print(f"      🗑️ Total supprimé : {lignes_initiales - len(df):,} lignes")

    print("\n" + "="*80)
    print("                    🔧 RECALCUL DU PU NET")
    print("="*80)
    
    # ═══════════════════════════════════════════════════════════════════
    # ÉTAPE 8.5 : SUPPRESSION DES OUTLIERS (méthode IQR)
    # ═══════════════════════════════════════════════════════════════════
    
    print("\n   📊 Étape 8.5 : Suppression des outliers (méthode IQR)...")
    
    lignes_avant_outliers = len(df)
    print(f"      📊 Lignes avant suppression outliers : {lignes_avant_outliers:,}")
    
    # Outliers sur Montant
    Q1 = df['Montant'].quantile(0.25)
    Q3 = df['Montant'].quantile(0.75)
    IQR = Q3 - Q1
    lower_bound = Q1 - 1.5 * IQR
    upper_bound = Q3 + 1.5 * IQR
    
    outliers_montant = ((df['Montant'] < lower_bound) | (df['Montant'] > upper_bound)).sum()
    df = df[(df['Montant'] >= lower_bound) & (df['Montant'] <= upper_bound)]
    print(f"      ❌ Supprimé {outliers_montant:,} outliers sur Montant (Q1={Q1:.2f}, Q3={Q3:.2f}, IQR={IQR:.2f})")
    
    # Outliers sur Quantité
    Q1_qty = df['Quantité'].quantile(0.25)
    Q3_qty = df['Quantité'].quantile(0.75)
    IQR_qty = Q3_qty - Q1_qty
    lower_bound_qty = Q1_qty - 1.5 * IQR_qty
    upper_bound_qty = Q3_qty + 1.5 * IQR_qty
    
    outliers_qty = ((df['Quantité'] < lower_bound_qty) | (df['Quantité'] > upper_bound_qty)).sum()
    df = df[(df['Quantité'] >= lower_bound_qty) & (df['Quantité'] <= upper_bound_qty)]
    print(f"      ❌ Supprimé {outliers_qty:,} outliers sur Quantité (Q1={Q1_qty:.2f}, Q3={Q3_qty:.2f}, IQR={IQR_qty:.2f})")
    
    lignes_apres_outliers = len(df)
    total_outliers = lignes_avant_outliers - lignes_apres_outliers
    print(f"      ✅ Total outliers supprimés : {total_outliers:,} lignes ({(total_outliers/lignes_avant_outliers*100):.2f}%)")
    
    # ═══════════════════════════════════════════════════════════════════
    # ÉTAPE 9 : RECALCUL DU PU NET
    # ═══════════════════════════════════════════════════════════════════
    
    print("\n   🔧 Étape 9 : Recalcul du PU Net...")
    
    df['PU Net'] = df['Montant'] / df['Quantité']
    print(f"      ✅ PU Net recalculé (Min : {df['PU Net'].min():.2f}€, Max : {df['PU Net'].max():.2f}€)")
    
    # Outliers sur PU Net (après recalcul)
    Q1_pu = df['PU Net'].quantile(0.25)
    Q3_pu = df['PU Net'].quantile(0.75)
    IQR_pu = Q3_pu - Q1_pu
    lower_bound_pu = Q1_pu - 1.5 * IQR_pu
    upper_bound_pu = Q3_pu + 1.5 * IQR_pu
    
    outliers_pu = ((df['PU Net'] < lower_bound_pu) | (df['PU Net'] > upper_bound_pu)).sum()
    df = df[(df['PU Net'] >= lower_bound_pu) & (df['PU Net'] <= upper_bound_pu)]
    print(f"      ❌ Supprimé {outliers_pu:,} outliers sur PU Net (Q1={Q1_pu:.2f}, Q3={Q3_pu:.2f}, IQR={IQR_pu:.2f})")
    
    # ═══════════════════════════════════════════════════════════════════
    # ÉTAPE 10 : CONVERSION DES DEVISES EN EURO
    # ═══════════════════════════════════════════════════════════════════
    
    print("\n   💱 Étape 10 : Conversion des devises...")
    
    if 'Nom Devise' in df.columns:
        taux_change = {
            'EURO': 1.0,
            'LIVRE STER': 1.20,  # 1 GBP = 1.20 EUR
            'DOLLAR US': 0.92    # 1 USD = 0.92 EUR
        }
        
        nb_converties = 0
        for devise, taux in taux_change.items():
            if devise != 'EURO':
                mask = (df['Nom Devise'] == devise)
                nb = mask.sum()
                if nb > 0:
                    df.loc[mask, 'Montant'] = df.loc[mask, 'Montant'] * taux
                    df.loc[mask, 'PU Net'] = df.loc[mask, 'PU Net'] * taux
                    nb_converties += nb
                    print(f"      ✅ {devise} : {nb:,} lignes converties (taux {taux})")
        
        print(f"      📊 Total converti : {nb_converties:,} lignes")
    
    # ═══════════════════════════════════════════════════════════════════
    # ÉTAPE 11 : CRÉATION DU DATASET FINAL
    # ═══════════════════════════════════════════════════════════════════
    
    print("\n   📋 Étape 11 : Création du dataset final...")
    
    colonnes_finales = [
        # Dates & Temps
        'Date Fact.', 'Date Cde', 'Year', 'Month', 'Quarter', 'Weekday', 'Day',
        # Client
        'Cpt Client', 'Intitulé', 'Country', 'Cumulative_Sales_Client', 'Rolling_3M_Sales',
        # Produit
        'Libelle 1', 'Famille',
        # Financier
        'Montant', 'PU Net', 'Quantité',
        # Commande
        'N° Bon',
        # Délai
        'Delai_Prev_Days', 'Delay_Deviation'
    ]
    
    # Sélectionner uniquement les colonnes qui existent
    colonnes_existantes = [col for col in colonnes_finales if col in df.columns]
    df_final = df[colonnes_existantes].copy()
    
    # Conversion finale des dates
    df_final['Date Fact.'] = pd.to_datetime(df_final['Date Fact.'], errors='coerce')
    df_final['Date Cde'] = pd.to_datetime(df_final['Date Cde'], errors='coerce')
    
    print(f"      ✅ Dataset final : {len(df_final):,} lignes × {len(df_final.columns)} colonnes")
    print(f"\n🎉 Traitement terminé ! (Identique au notebook)")
    
    return df_final
