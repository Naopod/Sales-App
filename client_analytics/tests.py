from django.test import TestCase, Client
from django.urls import reverse
from .models import Dataset
from django.core.files.uploadedfile import SimpleUploadedFile
import os


class DatasetModelTest(TestCase):
    """Test Dataset model"""
    
    def test_create_uploaded_dataset(self):
        """Test creating a dataset with upload source"""
        dataset = Dataset.objects.create(
            name='Test Dataset',
            source_type='upload'
        )
        self.assertEqual(dataset.name, 'Test Dataset')
        self.assertEqual(dataset.source_type, 'upload')
        self.assertIsNotNone(dataset.created_at)
    
    def test_create_stored_dataset(self):
        """Test creating a dataset with stored source"""
        dataset = Dataset.objects.create(
            name='Demo Dataset',
            source_type='stored',
            stored_key='demo_clients_1.xlsx'
        )
        self.assertEqual(dataset.source_type, 'stored')
        self.assertEqual(dataset.stored_key, 'demo_clients_1.xlsx')


class ViewsTest(TestCase):
    """Test views"""
    
    def setUp(self):
        self.client = Client()
    
    def test_home_view_get(self):
        """Test home view GET request"""
        response = self.client.get(reverse('client_analytics:home'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'upload')
    
    def test_workflow_view(self):
        """Test workflow view"""
        response = self.client.get(reverse('client_analytics:workflow'))
        self.assertEqual(response.status_code, 200)
    
    def test_dataset_overview_view(self):
        """Test dataset overview with stored dataset"""
        dataset = Dataset.objects.create(
            name='Test Demo',
            source_type='stored',
            stored_key='demo_clients_1.xlsx'
        )
        response = self.client.get(
            reverse('client_analytics:dataset_overview', kwargs={'pk': dataset.pk})
        )
        # Will return 302 or 200 depending on whether demo file exists
        self.assertIn(response.status_code, [200, 302])


class FormTest(TestCase):
    """Test forms"""
    
    def test_upload_form_valid(self):
        """Test upload form with valid data"""
        from .forms import UploadDatasetForm
        
        file_content = b'test content'
        file = SimpleUploadedFile('test.xlsx', file_content, content_type='application/vnd.ms-excel')
        
        form = UploadDatasetForm(
            data={'name': 'Test Upload'},
            files={'file': file}
        )
        self.assertTrue(form.is_valid())
    
    def test_upload_form_invalid_extension(self):
        """Test upload form with invalid file extension"""
        from .forms import UploadDatasetForm
        
        file_content = b'test content'
        file = SimpleUploadedFile('test.txt', file_content, content_type='text/plain')
        
        form = UploadDatasetForm(
            data={'name': 'Test Upload'},
            files={'file': file}
        )
        self.assertFalse(form.is_valid())
