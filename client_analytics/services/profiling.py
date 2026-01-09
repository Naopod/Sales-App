"""
Dataset Profiling Service - Basic dataset information
"""
import pandas as pd
import numpy as np


def get_dataset_info(df):
    """
    Get basic dataset information
    
    Args:
        df: pandas.DataFrame
        
    Returns:
        dict with dataset info
    """
    info = {
        'shape': df.shape,
        'num_rows': df.shape[0],
        'num_cols': df.shape[1],
        'columns': list(df.columns),
        'dtypes': df.dtypes.astype(str).to_dict(),
        'memory_usage': df.memory_usage(deep=True).sum(),
    }
    return info


def get_missing_values(df):
    """
    Get missing values information
    
    Args:
        df: pandas.DataFrame
        
    Returns:
        dict with missing values count and percentage
    """
    missing = df.isnull().sum()
    missing_pct = (missing / len(df) * 100).round(2)
    
    missing_info = []
    for col in df.columns:
        if missing[col] > 0:
            missing_info.append({
                'column': col,
                'count': int(missing[col]),
                'percentage': float(missing_pct[col])
            })
    
    return missing_info


def get_numeric_summary(df):
    """
    Get summary statistics for numeric columns
    
    Args:
        df: pandas.DataFrame
        
    Returns:
        pandas.DataFrame with describe() output
    """
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    if len(numeric_cols) == 0:
        return None
    
    return df[numeric_cols].describe()


def get_categorical_summary(df, max_categories=20):
    """
    Get summary for categorical columns
    
    Args:
        df: pandas.DataFrame
        max_categories: max number of unique values to consider as categorical
        
    Returns:
        dict with categorical column info
    """
    categorical_info = []
    
    for col in df.columns:
        if df[col].dtype == 'object' or df[col].nunique() < max_categories:
            unique_count = df[col].nunique()
            categorical_info.append({
                'column': col,
                'unique_count': int(unique_count),
                'most_common': df[col].value_counts().head(5).to_dict()
            })
    
    return categorical_info


def get_column_types(df):
    """
    Classify columns into numeric and categorical
    
    Args:
        df: pandas.DataFrame
        
    Returns:
        dict with 'numeric' and 'categorical' column lists
    """
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    categorical_cols = df.select_dtypes(exclude=[np.number]).columns.tolist()
    
    return {
        'numeric': numeric_cols,
        'categorical': categorical_cols
    }
