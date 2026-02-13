"""
Script de validation rapide pour l'analyse de dépendance à la devise

Crée un DataFrame de test et vérifie que toutes les fonctions s'exécutent correctement.
"""

import sys

import pandas as pd
import numpy as np
from datetime import datetime, timedelta


# Assure un affichage UTF-8 (évite UnicodeEncodeError sous Windows/cp1252)
try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except Exception:
    pass

# Test d'import
print("Test d'import des modules...")
try:
    from client_analytics.services.currency_dependency import (
        analyze_currency_dependency,
        normalize_currency,
        compute_kpi,
        clean_dataframe
    )
    print("   OK: Import currency_dependency")
except ImportError as e:
    print(f"   ERREUR import: {e}")
    exit(1)

# Créer un DataFrame de test
print("\nCréation d'un DataFrame de test...")

np.random.seed(42)
n_rows = 1000

# Dates
start_date = datetime(2024, 1, 1)
dates = [start_date + timedelta(days=i) for i in range(365)]
date_fact = np.random.choice(dates, n_rows)

# Devises
devises = ['EUR'] * 700 + ['USD'] * 200 + ['GBP'] * 60 + ['CHF'] * 30 + ['CAD'] * 10
np.random.shuffle(devises)

# Montants
montants = np.random.uniform(100, 10000, n_rows)

# Pays
pays_map = {'EUR': 'FR', 'USD': 'US', 'GBP': 'GB', 'CHF': 'CH', 'CAD': 'CA'}
pays = [pays_map[d] for d in devises]

# Clients
clients = [f"Client_{i:03d}" for i in np.random.randint(1, 51, n_rows)]

# Familles
familles = np.random.choice(['PROD', 'SERV', 'MAINT', 'CONSULT'], n_rows)

df_test = pd.DataFrame({
    'Date Fact.': date_fact,
    'Montant': montants,
    'Nom Devise': devises,
    'Country': pays,
    'Intitulé': clients,
    'Famille': familles
})

print(f"   OK: DataFrame créé: {len(df_test):,} lignes x {len(df_test.columns)} colonnes")

# Test 1: Nettoyage
print("\nTest 1: Nettoyage du DataFrame...")
try:
    df_clean = clean_dataframe(df_test)
    print(f"   OK: Nettoyage ({len(df_clean):,} lignes après nettoyage)")
except Exception as e:
    print(f"   ERREUR: {e}")
    exit(1)

# Test 2: Calcul KPI
print("\nTest 2: Calcul des KPI...")
try:
    kpi = compute_kpi(df_clean)
    
    if 'error' in kpi:
        print(f"   ERREUR KPI: {kpi['error']}")
        exit(1)
    
    print(f"   OK: CA total: {kpi['total_revenue']:,.2f} €")
    print(f"   OK: Part non-EUR: {kpi['non_eur_pct']:.2f}%")
    print(f"   OK: Devises détectées: {len(kpi['currencies_detected'])}")
    print(f"   OK: HHI: {kpi['hhi_currency']:.2f}")
    
except Exception as e:
    print(f"   ERREUR: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

# Test 3: Analyse complète (sans sauvegarde)
print("\nTest 3: Analyse complète...")
try:
    report = analyze_currency_dependency(df_clean, output_dir=None)
    
    kpi = report['kpi']
    charts = report['charts']
    
    print(f"   OK: KPI générés: {len(kpi)} entrées")
    print(f"   OK: Graphiques générés: {len(charts)}")
    
    # Détail des graphiques
    for chart_name in charts.keys():
        print(f"      - {chart_name}")
    
except Exception as e:
    print(f"   ERREUR: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

# Test 4: Analyse avec sauvegarde
print("\nTest 4: Analyse avec sauvegarde des graphiques...")
try:
    report = analyze_currency_dependency(df_clean, output_dir="outputs/test_currency")
    
    chart_paths = report['chart_paths']
    
    print(f"   OK: Graphiques sauvegardés: {len(chart_paths)}")
    for name, path in chart_paths.items():
        print(f"      - {name}: {path}")
    
except Exception as e:
    print(f"   ERREUR: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

# Test 5: Robustesse (colonnes manquantes)
print("\nTest 5: Robustesse avec colonnes manquantes...")
try:
    df_minimal = df_test[['Montant']].copy()
    
    report = analyze_currency_dependency(df_minimal, output_dir=None)
    kpi = report['kpi']
    
    if 'error' in kpi:
        print(f"   ATTENDU: {kpi['error']}")
    else:
        print(f"   OK: Module robuste: {kpi['total_revenue']:,.2f} € calculés")
        print(f"   OK: Devises: {kpi['currencies_detected']}")
        print(f"   OK: Graphiques: {len(report['charts'])} générés")
    
except Exception as e:
    print(f"   ERREUR inattendue: {e}")
    exit(1)

print("\n" + "=" * 80)
print("   OK: TOUS LES TESTS SONT PASSÉS AVEC SUCCÈS!")
print("=" * 80)
print("\nINFO: Le module currency_dependency est prêt à être utilisé.")
print("INFO: Consultez example_currency_usage.py pour des exemples d'utilisation.")
print("INFO: Consultez CURRENCY_DEPENDENCY_README.md pour la documentation complète.")
