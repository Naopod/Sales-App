import numpy as np

"""
Service pour l'onglet OVERVIEW
Génère les informations de profiling de base du dataset
"""


def get_dataset_info(df):
    """
    Informations de base sur le dataset

    Args:
        df: pandas.DataFrame

    Returns:
        dict avec les infos du dataset
    """
    info = {
        "shape": df.shape,
        "num_rows": df.shape[0],
        "num_cols": df.shape[1],
        "columns": list(df.columns),
        "dtypes": df.dtypes.astype(str).to_dict(),
        "memory_usage": df.memory_usage(deep=True).sum(),
    }
    return info


def get_missing_values(df):
    """
    Informations sur les valeurs manquantes

    Args:
        df: pandas.DataFrame

    Returns:
        list de dict avec les valeurs manquantes par colonne
    """
    missing = df.isnull().sum()
    missing_pct = (missing / len(df) * 100).round(2)

    missing_info = []
    for col in df.columns:
        if missing[col] > 0:
            missing_info.append(
                {
                    "column": col,
                    "count": int(missing[col]),
                    "percentage": float(missing_pct[col]),
                }
            )

    return missing_info


def get_column_types(df):
    """
    Classifie les colonnes en numériques et catégorielles

    Args:
        df: pandas.DataFrame

    Returns:
        dict avec les types de colonnes
    """
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    categorical_cols = df.select_dtypes(include=["object", "category"]).columns.tolist()
    datetime_cols = df.select_dtypes(include=["datetime64"]).columns.tolist()

    return {
        "numeric": numeric_cols,
        "categorical": categorical_cols,
        "datetime": datetime_cols,
    }


def generate_overview_analysis(df):
    """
    Génère une analyse complète pour l'onglet Overview

    Args:
        df: pandas.DataFrame

    Returns:
        dict avec toutes les analyses pour l'onglet Overview
    """

    return {
        "info": get_dataset_info(df),
        "missing_info": get_missing_values(df),
        "column_types": get_column_types(df),
    }
