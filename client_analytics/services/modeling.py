"""
Machine Learning Modeling Service
"""
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.impute import SimpleImputer
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.linear_model import LogisticRegression, LinearRegression
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.metrics import (
    accuracy_score, f1_score, confusion_matrix,
    mean_squared_error, r2_score
)
import plotly.figure_factory as ff
import plotly.express as px


def detect_task_type(df, target_column):
    """Detect if task is classification or regression"""
    if target_column not in df.columns:
        return None
    
    target = df[target_column]
    
    # If target is numeric and has many unique values, it's likely regression
    if pd.api.types.is_numeric_dtype(target):
        unique_ratio = target.nunique() / len(target)
        if unique_ratio > 0.05:  # More than 5% unique values
            return 'regression'
        else:
            return 'classification'
    else:
        return 'classification'


def prepare_data(df, target_column, feature_columns):
    """Prepare data for modeling"""
    # Remove rows with missing target
    df_clean = df[[target_column] + feature_columns].dropna(subset=[target_column])
    
    if len(df_clean) < 10:
        raise ValueError("Dataset trop petit après nettoyage (minimum 10 lignes requises)")
    
    X = df_clean[feature_columns]
    y = df_clean[target_column]
    
    # Identify numeric and categorical columns
    numeric_features = X.select_dtypes(include=[np.number]).columns.tolist()
    categorical_features = X.select_dtypes(exclude=[np.number]).columns.tolist()
    
    return X, y, numeric_features, categorical_features


def create_preprocessing_pipeline(numeric_features, categorical_features):
    """Create preprocessing pipeline"""
    transformers = []
    
    if numeric_features:
        numeric_transformer = Pipeline(steps=[
            ('imputer', SimpleImputer(strategy='median')),
            ('scaler', StandardScaler())
        ])
        transformers.append(('num', numeric_transformer, numeric_features))
    
    if categorical_features:
        categorical_transformer = Pipeline(steps=[
            ('imputer', SimpleImputer(strategy='most_frequent')),
            ('onehot', OneHotEncoder(handle_unknown='ignore', sparse_output=False))
        ])
        transformers.append(('cat', categorical_transformer, categorical_features))
    
    preprocessor = ColumnTransformer(transformers=transformers)
    return preprocessor


def train_model(df, target_column, feature_columns, model_type, task_type):
    """
    Train a machine learning model
    
    Args:
        df: pandas.DataFrame
        target_column: str
        feature_columns: list of str
        model_type: str ('logistic', 'rf_classifier', 'linear', 'rf_regressor')
        task_type: str ('classification', 'regression')
        
    Returns:
        dict with results
    """
    try:
        # Prepare data
        X, y, numeric_features, categorical_features = prepare_data(
            df, target_column, feature_columns
        )
        
        # Split data
        test_size = 0.2 if len(X) > 50 else 0.3
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size, random_state=42
        )
        
        # Create preprocessing pipeline
        preprocessor = create_preprocessing_pipeline(numeric_features, categorical_features)
        
        # Select model
        if task_type == 'classification':
            if model_type == 'logistic':
                model = LogisticRegression(max_iter=1000, random_state=42)
            else:  # rf_classifier
                model = RandomForestClassifier(n_estimators=100, random_state=42)
        else:  # regression
            if model_type == 'linear':
                model = LinearRegression()
            else:  # rf_regressor
                model = RandomForestRegressor(n_estimators=100, random_state=42)
        
        # Create full pipeline
        pipeline = Pipeline(steps=[
            ('preprocessor', preprocessor),
            ('model', model)
        ])
        
        # Train
        pipeline.fit(X_train, y_train)
        
        # Predict
        y_pred = pipeline.predict(X_test)
        
        # Calculate metrics
        results = {
            'success': True,
            'task_type': task_type,
            'model_type': model_type,
            'train_size': len(X_train),
            'test_size': len(X_test),
            'feature_columns': feature_columns,
            'numeric_features': numeric_features,
            'categorical_features': categorical_features,
        }
        
        if task_type == 'classification':
            accuracy = accuracy_score(y_test, y_pred)
            f1 = f1_score(y_test, y_pred, average='weighted')
            conf_mat = confusion_matrix(y_test, y_pred)
            
            results['accuracy'] = float(accuracy)
            results['f1_score'] = float(f1)
            results['confusion_matrix'] = conf_mat.tolist()
            results['confusion_matrix_html'] = create_confusion_matrix_plot(
                conf_mat, sorted(y.unique())
            )
        else:  # regression
            mse = mean_squared_error(y_test, y_pred)
            rmse = np.sqrt(mse)
            r2 = r2_score(y_test, y_pred)
            
            results['rmse'] = float(rmse)
            results['r2'] = float(r2)
            results['mse'] = float(mse)
        
        # Feature importance (for Random Forest)
        if model_type in ['rf_classifier', 'rf_regressor']:
            feature_importance = get_feature_importance(
                pipeline, feature_columns, numeric_features, categorical_features
            )
            results['feature_importance'] = feature_importance
            results['feature_importance_html'] = create_feature_importance_plot(
                feature_importance
            )
        
        return results
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }


def get_feature_importance(pipeline, feature_columns, numeric_features, categorical_features):
    """Extract feature importance from Random Forest model"""
    model = pipeline.named_steps['model']
    
    if not hasattr(model, 'feature_importances_'):
        return None
    
    # Get feature names after preprocessing
    preprocessor = pipeline.named_steps['preprocessor']
    
    feature_names = []
    if numeric_features:
        feature_names.extend(numeric_features)
    if categorical_features:
        # Get feature names from OneHotEncoder
        cat_encoder = preprocessor.named_transformers_['cat'].named_steps['onehot']
        cat_feature_names = cat_encoder.get_feature_names_out(categorical_features)
        feature_names.extend(cat_feature_names)
    
    importances = model.feature_importances_
    
    # Create list of tuples (feature, importance)
    feature_importance = [
        {'feature': name, 'importance': float(imp)}
        for name, imp in zip(feature_names, importances)
    ]
    
    # Sort by importance
    feature_importance = sorted(
        feature_importance,
        key=lambda x: x['importance'],
        reverse=True
    )[:20]  # Top 20
    
    return feature_importance


def create_confusion_matrix_plot(conf_mat, labels):
    """Create confusion matrix heatmap"""
    fig = ff.create_annotated_heatmap(
        z=conf_mat,
        x=[str(l) for l in labels],
        y=[str(l) for l in labels],
        colorscale='Blues',
        showscale=True
    )
    
    fig.update_layout(
        title='Matrice de Confusion',
        xaxis_title='Prédiction',
        yaxis_title='Valeur Réelle',
        height=400
    )
    
    return fig.to_html(full_html=False, include_plotlyjs='cdn')


def create_feature_importance_plot(feature_importance):
    """Create feature importance bar chart"""
    df_imp = pd.DataFrame(feature_importance)
    
    fig = px.bar(
        df_imp,
        x='importance',
        y='feature',
        orientation='h',
        title='Importance des Features (Top 20)',
        labels={'importance': 'Importance', 'feature': 'Feature'}
    )
    
    fig.update_layout(
        template='plotly_white',
        height=max(400, len(df_imp) * 25),
        yaxis={'categoryorder': 'total ascending'}
    )
    
    return fig.to_html(full_html=False, include_plotlyjs='cdn')
