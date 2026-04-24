import pandas as pd

from django.test import SimpleTestCase, override_settings

from client_analytics.services import analysis_clustering


class QuarterlyClusteringTests(SimpleTestCase):
    def _build_quarterly_dataset(self, year=2024):
        rows = []
        quarter_months = {
            f"{year}Q1": [1, 2],
            f"{year}Q2": [4, 5],
            f"{year}Q3": [7, 8],
            f"{year}Q4": [10, 11],
        }

        for quarter, months in quarter_months.items():
            for idx in range(8):
                client = f"C{idx + 1:02d}"
                is_vip = idx < 4
                country = "FR" if is_vip else "DE"

                for order_no, month in enumerate(months, start=1):
                    rows.append(
                        {
                            "Cpt Client": client,
                            "Date Cde": pd.Timestamp(year, month, 5 + idx),
                            "Montant": 1500.0 + idx * 20 if is_vip else 150.0 + idx * 5,
                            "Quantité": 120 + idx if is_vip else 15 + idx,
                            "Delai_Prev_Days": 4 if is_vip else 12,
                            "N° Bon": f"{quarter}-{client}-{order_no}",
                            "Famille": "VIP" if order_no == 1 else "CORE",
                            "PU Net": 12.0 if is_vip else 4.0,
                            "Country": country,
                            "Quarter": quarter,
                        }
                    )

        return pd.DataFrame(rows)

    def test_get_quarterly_clustering_available_years_lists_all_years(self):
        df = pd.concat(
            [
                self._build_quarterly_dataset(2024),
                self._build_quarterly_dataset(2025),
            ],
            ignore_index=True,
        )

        years = analysis_clustering.get_quarterly_clustering_available_years(df)

        self.assertEqual(years, [2024, 2025])

    def test_generate_quarterly_clustering_analysis_returns_notebook_outputs(self):
        df = self._build_quarterly_dataset()

        result = analysis_clustering.generate_quarterly_clustering_analysis(df)

        self.assertNotIn("error", result)
        self.assertEqual(result["kpis"]["annee_analysee"], 2024)
        self.assertEqual(result["kpis"]["nb_trimestres"], 4)
        self.assertGreaterEqual(result["kpis"]["k_fixed"], 2)
        self.assertEqual(
            result["results"]["closed_periods"],
            [("2024-08-01", "2024-08-26")],
        )
        self.assertEqual(len(result["results"]["transition_tables"]), 3)
        self.assertTrue(result["graphs"]["transition_heatmap"])

    def test_generate_quarterly_clustering_analysis_supports_selected_year(self):
        df = pd.concat(
            [
                self._build_quarterly_dataset(2024),
                self._build_quarterly_dataset(2025),
            ],
            ignore_index=True,
        )

        result = analysis_clustering.generate_quarterly_clustering_analysis(
            df,
            year=2025,
        )

        self.assertNotIn("error", result)
        self.assertEqual(result["kpis"]["annee_analysee"], 2025)
        self.assertEqual(result["kpis"]["nb_trimestres"], 4)
        self.assertEqual(result["kpis"]["nb_clients"], 8)
        self.assertEqual(result["results"]["closed_periods"], [])
        self.assertEqual(len(result["results"]["transition_tables"]), 3)
        self.assertTrue(result["graphs"]["transition_heatmap"])

    @override_settings(
        CLUSTERING_NOTEBOOK_CLOSED_PERIODS_BY_YEAR={
            2024: [("2024-08-01", "2024-08-26")],
            2025: [("2025-08-04", "2025-08-22")],
        }
    )
    def test_generate_quarterly_clustering_analysis_uses_settings_for_closed_periods(self):
        df = self._build_quarterly_dataset(2025)

        result = analysis_clustering.generate_quarterly_clustering_analysis(
            df,
            year=2025,
        )

        self.assertNotIn("error", result)
        self.assertEqual(
            result["results"]["closed_periods"],
            [("2025-08-04", "2025-08-22")],
        )

    def test_generate_quarterly_clustering_analysis_requires_selected_year_data(self):
        df = pd.DataFrame(
            {
                "Cpt Client": ["A"],
                "Date Cde": pd.to_datetime(["2025-01-03"]),
                "Montant": [100.0],
                "Quantité": [1],
                "Delai_Prev_Days": [5],
                "N° Bon": ["B1"],
                "Famille": ["CORE"],
                "PU Net": [10.0],
                "Country": ["FR"],
            }
        )

        result = analysis_clustering.generate_quarterly_clustering_analysis(
            df,
            year=2024,
        )

        self.assertIn("error", result)
        self.assertIn("2024", result["error"])
