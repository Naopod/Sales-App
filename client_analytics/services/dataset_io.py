"""
Dataset I/O Service - Loading datasets from uploads or demo data
"""
import pandas as pd
import os
from django.conf import settings


def load_dataset_df(dataset):
    """
    Load a pandas DataFrame from a Dataset model instance
    
    Args:
        dataset: Dataset model instance
        
    Returns:
        pandas.DataFrame or None if error
    """
    file_path = dataset.get_file_path()
    
    if not file_path or not os.path.exists(file_path):
        return None
    
    try:
        df = pd.read_excel(file_path)
        return df
    except Exception as e:
        print(f"Error loading dataset: {e}")
        return None


def get_demo_datasets():
    """
    Get list of available demo datasets
    
    Returns:
        list of dict with 'filename' and 'display_name'
    """
    return [
        {
            'filename': 'demo_clients_1.xlsx',
            'display_name': 'Dataset Démo 1 - Données Clients Basiques'
        },
        {
            'filename': 'demo_clients_2.xlsx',
            'display_name': 'Dataset Démo 2 - Comportement d\'Achat'
        }
    ]


def check_demo_file_exists(filename):
    """Check if a demo file exists"""
    demo_path = os.path.join(
        settings.BASE_DIR,
        'client_analytics',
        'demo_data',
        filename
    )
    return os.path.exists(demo_path)
