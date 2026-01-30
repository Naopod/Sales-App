"""
Script de test pour vérifier les nouvelles fonctionnalités d'analyse
"""
import os
import django
import pandas as pd
import numpy as np

# Configuration Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'analytics_portal.settings')
django.setup()

from client_analytics.services.visualizations import viz_by_period
from client_analytics.services.analysis_by_period import analyze_correlations_detailed, generate_deep_synthesis

# Créer des données de test
print("Création de données de test...")
np.random.seed(42)
n = 1000

df_test = pd.DataFrame({
    'Montant': np.random.lognormal(5, 1, n),
    'Quantité': np.random.poisson(10, n),
    'PU Net': np.random.gamma(2, 50, n),
    'Cpt Client': [f'Client_{i%100}' for i in range(n)],
    'Country': np.random.choice(['France', 'Germany', 'UK', 'Italy', 'Spain'], n),
    'Month': np.random.choice(['2024-01', '2024-02', '2024-03'], n)
})

print(f"✓ {len(df_test)} lignes de test créées")

# Test 1: QQ-Plot
print("\n1. Test QQ-Plot...")
try:
    qq_plot = viz_by_period.create_qq_plot(df_test, 'Montant')
    if qq_plot and len(qq_plot) > 100:
        print("   ✓ QQ-Plot généré avec succès")
    else:
        print("   ✗ Erreur: QQ-Plot vide")
except Exception as e:
    print(f"   ✗ Erreur QQ-Plot: {e}")

# Test 2: Test de normalité
print("\n2. Test de normalité avec courbe...")
try:
    norm_test = viz_by_period.create_normality_test_plot(df_test, 'Montant')
    if norm_test and len(norm_test) > 100:
        print("   ✓ Test de normalité généré avec succès")
    else:
        print("   ✗ Erreur: Test de normalité vide")
except Exception as e:
    print(f"   ✗ Erreur test normalité: {e}")

# Test 3: Boxplot des outliers
print("\n3. Test Boxplot outliers...")
try:
    boxplot = viz_by_period.create_outliers_boxplot(df_test, ['Montant', 'Quantité', 'PU Net'])
    if boxplot and len(boxplot) > 100:
        print("   ✓ Boxplot généré avec succès")
    else:
        print("   ✗ Erreur: Boxplot vide")
except Exception as e:
    print(f"   ✗ Erreur boxplot: {e}")

# Test 4: Analyse des corrélations
print("\n4. Test analyse corrélations...")
try:
    corr_analysis = analyze_correlations_detailed(df_test, ['Montant', 'Quantité', 'PU Net'])
    if corr_analysis and len(corr_analysis) > 50:
        print("   ✓ Analyse des corrélations générée avec succès")
        print(f"   Longueur: {len(corr_analysis)} caractères")
    else:
        print("   ✗ Erreur: Analyse vide")
except Exception as e:
    print(f"   ✗ Erreur analyse corrélations: {e}")

# Test 5: Synthèse approfondie
print("\n5. Test synthèse approfondie...")
try:
    kpis = {
        'total_transactions': '1,000',
        'ca_total': '150,000.00 €',
        'nb_clients': '100',
        'panier_moyen': '150.00 €'
    }
    synthesis = generate_deep_synthesis(df_test, kpis, ['Montant', 'Quantité', 'PU Net'])
    if synthesis and len(synthesis) > 500:
        print("   ✓ Synthèse approfondie générée avec succès")
        print(f"   Longueur: {len(synthesis)} caractères")
    else:
        print("   ✗ Erreur: Synthèse vide ou trop courte")
except Exception as e:
    print(f"   ✗ Erreur synthèse: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*60)
print("Tests terminés !")
print("="*60)
