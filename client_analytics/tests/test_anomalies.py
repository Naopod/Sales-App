import pandas as pd

from django.test import SimpleTestCase


class ClientPortfolioAnomaliesTests(SimpleTestCase):
    def test_detects_ca_spike_in_latest_month(self):
        from client_analytics.services.analysis_anomalies import analyze_client_anomalies

        months = pd.date_range('2024-01-01', periods=12, freq='MS')
        rows = []
        order_id = 1
        for month_start in months:
            for _ in range(5):
                rows.append(
                    {
                        'Cpt Client': 'A',
                        'Date Fact.': month_start,
                        'Montant': 1000.0 if month_start == months[-1] else 100.0,
                        'Quantité': 10.0,
                        'N° Bon': f'CMD_{order_id}',
                    }
                )
                order_id += 1

            for _ in range(5):
                rows.append(
                    {
                        'Cpt Client': 'B',
                        'Date Fact.': month_start,
                        'Montant': 120.0,
                        'Quantité': 10.0,
                        'N° Bon': f'CMD_{order_id}',
                    }
                )
                order_id += 1

        df = pd.DataFrame(rows)
        report = analyze_client_anomalies(
            df,
            time_granularity='month',
            z_thresh=3.5,
            window=6,
            min_history=6,
            top_n=10,
            include_scatter=False,
        )

        self.assertNotIn('error', report)
        self.assertIn('kpis', report)
        self.assertEqual(report['kpis'].get('latest_period'), '2024-12')

        top = report.get('top_anomalies_latest', [])
        self.assertTrue(len(top) >= 1)
        self.assertEqual(top[0]['client'], 'A')

    def test_detects_ca_spike_for_selected_client(self):
        from client_analytics.services.analysis_anomalies import analyze_client_anomalies_for_client

        months = pd.date_range('2024-01-01', periods=12, freq='MS')
        rows = []
        order_id = 1
        for month_start in months:
            for _ in range(5):
                rows.append(
                    {
                        'Cpt Client': 'A',
                        'Date Fact.': month_start,
                        'Montant': 1000.0 if month_start == months[-1] else 100.0,
                        'Quantité': 10.0,
                        'N° Bon': f'CMD_{order_id}',
                    }
                )
                order_id += 1

            for _ in range(5):
                rows.append(
                    {
                        'Cpt Client': 'B',
                        'Date Fact.': month_start,
                        'Montant': 120.0,
                        'Quantité': 10.0,
                        'N° Bon': f'CMD_{order_id}',
                    }
                )
                order_id += 1

        df = pd.DataFrame(rows)
        report = analyze_client_anomalies_for_client(
            df,
            client_id='A',
            time_granularity='month',
            z_thresh=3.5,
            window=6,
            min_history=6,
        )

        self.assertNotIn('error', report)
        self.assertEqual(report.get('kpis', {}).get('latest_period'), '2024-12')
        ca_anoms = report.get('anomalies_by_metric', {}).get('CA', [])
        self.assertTrue(any(r.get('period') == '2024-12' for r in ca_anoms))
