"""
Dataset I/O Service - Loading datasets from uploads
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
        return None



