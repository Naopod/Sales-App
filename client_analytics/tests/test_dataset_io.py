from unittest.mock import patch

from django.test import SimpleTestCase

from client_analytics.services import dataset_io


class DatasetIoTests(SimpleTestCase):
    def test_xlsx_uses_openpyxl(self):
        with patch("client_analytics.services.dataset_io.pd.read_excel", return_value="ok") as mock_read:
            result = dataset_io.read_excel_file(__file__.replace(".py", ".xlsx"))

        self.assertEqual(result, "ok")
        mock_read.assert_called_once_with(__file__.replace(".py", ".xlsx"), engine="openpyxl")

    def test_xls_falls_back_to_openpyxl_for_mislabeled_modern_file(self):
        calls = []

        def fake_read_excel(path, engine):
            calls.append(engine)
            if engine == "xlrd":
                raise ValueError("Unsupported format")
            return "ok"

        with patch("client_analytics.services.dataset_io.os.path.exists", return_value=True):
            with patch("client_analytics.services.dataset_io.pd.read_excel", side_effect=fake_read_excel):
                result = dataset_io.read_excel_file("legacy_processed.xls")

        self.assertEqual(result, "ok")
        self.assertEqual(calls, ["xlrd", "openpyxl"])

    def test_processed_output_name_is_normalized_to_xlsx(self):
        self.assertEqual(dataset_io.get_processed_output_name("raw_upload.xls"), "raw_upload.xlsx")
        self.assertEqual(dataset_io.get_processed_output_name("raw_upload.xlsx"), "raw_upload.xlsx")
