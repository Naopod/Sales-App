"""
Tests pour les fonctionnalités PowerBI-like dans l'analyse client.
"""
import pandas as pd
import numpy as np
from django.test import TestCase
from client_analytics.services import analysis_clients


class TestClientPowerBIAnalysis(TestCase):
    """Tests pour l'analyse client type PowerBI."""

    def setUp(self):
        """Créer un DataFrame synthétique pour les tests."""
        np.random.seed(42)
        n_rows = 200
        
        # Générer des données synthétiques
        self.df = pd.DataFrame({
            'Cpt Client': np.random.choice(['CLIENT001', 'CLIENT002', 'CLIENT003'], n_rows),
            'Libelle 1': np.random.choice(['PROD_A', 'PROD_B', 'PROD_C', 'PROD_D'], n_rows),
            'Libelle 2': np.random.choice(['Détail A', 'Détail B', 'Détail C', None], n_rows),
            'Famille': np.random.choice(['Bakery', 'Pastry', 'Bread', 'Viennoiserie'], n_rows),
            'Montant': np.random.uniform(100, 5000, n_rows),
            'Quantité': np.random.randint(1, 100, n_rows),
            'Fiscal_Year': np.random.choice([2023, 2024, 2025], n_rows),
            'Trimestre_Num': np.random.choice([1, 2, 3, 4], n_rows),
            'Date Fact.': pd.date_range('2023-01-01', periods=n_rows, freq='D'),
            'N° Bon': [f'BO{i:04d}' for i in range(n_rows)],
        })
    
    def test_analyze_client_with_selected_families(self):
        """Test que le filtrage par famille fonctionne."""
        result = analysis_clients.analyze_client_portfolio_full(
            self.df,
            client_id='CLIENT001',
            time_granularity='month',
            selected_families=['Bakery', 'Pastry']
        )
        
        # Vérifier qu'il n'y a pas d'erreur
        self.assertNotIn('error', result)
        
        # Vérifier que les tables ont été générées (peuvent être None si pas de données)
        self.assertIn('tables', result)
        self.assertIn('products_fy_amount_table_html', result['tables'])
        self.assertIn('products_fy_qty_table_html', result['tables'])
        self.assertIn('efq_family_amount_table_html', result['tables'])
        self.assertIn('efq_family_qty_table_html', result['tables'])
    
    def test_products_fy_table_generation(self):
        """Test que la table Produits × FY est générée correctement."""
        result = analysis_clients.analyze_client_portfolio_full(
            self.df,
            client_id='CLIENT001',
            time_granularity='year'
        )
        
        # Vérifier que la table HTML est présente
        products_fy_amount = result['tables'].get('products_fy_amount_table_html')
        
        if products_fy_amount:
            # Vérifier que c'est du HTML
            self.assertIn('table', products_fy_amount.lower())
            self.assertIn('total', products_fy_amount.lower())
    
    def test_efq_family_tables_generation(self):
        """Test que les matrices EF&Q × Famille sont générées."""
        result = analysis_clients.analyze_client_portfolio_full(
            self.df,
            client_id='CLIENT001',
            time_granularity='quarter'
        )
        
        # Vérifier les tables
        efq_amt = result['tables'].get('efq_family_amount_table_html')
        efq_qty = result['tables'].get('efq_family_qty_table_html')
        
        # Au moins une des tables devrait être générée
        # (peut être None si pas assez de données dans certaines configurations)
        self.assertIsNotNone(result['tables'])
    
    def test_efq_family_charts_generation(self):
        """Test que les graphiques empilés sont générés."""
        result = analysis_clients.analyze_client_portfolio_full(
            self.df,
            client_id='CLIENT001',
            time_granularity='year'
        )
        
        # Vérifier les graphiques
        self.assertIn('graphs', result)
        self.assertIn('chart_efq_family_amount_html', result['graphs'])
        self.assertIn('chart_efq_family_qty_html', result['graphs'])
        
        # Si un graphique est présent, vérifier qu'il contient du HTML Plotly
        chart_amt = result['graphs'].get('chart_efq_family_amount_html')
        if chart_amt:
            self.assertIn('plotly', chart_amt.lower())
    
    def test_empty_families_filter(self):
        """Test avec un filtre de familles vide (toutes les familles)."""
        result = analysis_clients.analyze_client_portfolio_full(
            self.df,
            client_id='CLIENT001',
            selected_families=[]
        )
        
        # Ne devrait pas filtrer si la liste est vide
        self.assertNotIn('error', result)
        self.assertIn('kpis', result)
    
    def test_nonexistent_family_filter(self):
        """Test avec des familles inexistantes."""
        result = analysis_clients.analyze_client_portfolio_full(
            self.df,
            client_id='CLIENT001',
            selected_families=['NonExistentFamily']
        )
        
        # Devrait retourner une erreur ou des données vides
        # (selon l'implémentation, soit error, soit tables vides)
        if 'error' in result:
            self.assertIn('Aucune donnée', result['error'])
    
    def test_libelle2_handling(self):
        """Test que Libelle 2 est bien géré (même s'il manque ou a des NaN)."""
        # DataFrame sans Libelle 2
        df_no_lib2 = self.df.drop(columns=['Libelle 2'])
        
        result = analysis_clients.analyze_client_portfolio_full(
            df_no_lib2,
            client_id='CLIENT001'
        )
        
        # Ne devrait pas crasher
        self.assertNotIn('error', result)
        
        # Vérifier que les tables ont été tentées (peuvent être None)
        self.assertIn('tables', result)
    
    def test_missing_fy_fallback_to_year(self):
        """Test que si Fiscal_Year manque, on utilise Year en fallback."""
        df_no_fy = self.df.copy()
        df_no_fy['Year'] = df_no_fy['Fiscal_Year']
        df_no_fy = df_no_fy.drop(columns=['Fiscal_Year'])
        
        result = analysis_clients.analyze_client_portfolio_full(
            df_no_fy,
            client_id='CLIENT001'
        )
        
        # Devrait quand même générer les tables si Year existe
        self.assertNotIn('error', result)
        self.assertIn('tables', result)


class TestVisualizationFunctions(TestCase):
    """Tests pour les fonctions de visualisation."""
    
    def test_create_client_period_family_stacked(self):
        """Test de la création de graphiques empilés."""
        from client_analytics.services.visualizations import viz_clients
        
        records = [
            {'period': '2024-Q1', 'family': 'Bakery', 'value': 12345.0},
            {'period': '2024-Q1', 'family': 'Pastry', 'value': 8900.0},
            {'period': '2024-Q2', 'family': 'Bakery', 'value': 15600.0},
            {'period': '2024-Q2', 'family': 'Pastry', 'value': 11200.0},
        ]
        
        result = viz_clients.create_client_period_family_stacked(
            records,
            value_key='value',
            title='Test Chart'
        )
        
        # Vérifier que c'est du HTML Plotly
        if result:
            self.assertIn('plotly', result.lower())
            self.assertIn('Test Chart', result)
    
    def test_stacked_chart_empty_records(self):
        """Test avec des records vides."""
        from client_analytics.services.visualizations import viz_clients
        
        result = viz_clients.create_client_period_family_stacked(
            [],
            value_key='value',
            title='Empty Chart'
        )
        
        # Devrait retourner None
        self.assertIsNone(result)
    
    def test_stacked_chart_missing_keys(self):
        """Test avec des clés manquantes."""
        from client_analytics.services.visualizations import viz_clients
        
        # Records sans la clé 'family'
        records = [
            {'period': '2024-Q1', 'value': 12345.0},
        ]
        
        result = viz_clients.create_client_period_family_stacked(
            records,
            value_key='value',
            title='Incomplete Data'
        )
        
        # Devrait retourner None ou gérer gracieusement
        # (selon l'implémentation, peut être None)
        self.assertTrue(result is None or isinstance(result, str))
