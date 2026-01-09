from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import HttpResponse
from .models import Dataset
from .forms import UploadDatasetForm, SelectDatasetForm
from .services import dataset_io, profiling, modeling, clustering
from .services import stats_complete, temporal_analysis
import pandas as pd


def home(request):
    """Home page with upload and selection forms"""
    upload_form = UploadDatasetForm()
    select_form = SelectDatasetForm()
    
    if request.method == 'POST':
        if 'upload' in request.POST:
            upload_form = UploadDatasetForm(request.POST, request.FILES)
            if upload_form.is_valid():
                dataset = upload_form.save()
                messages.success(request, f'Dataset "{dataset.name}" uploadé avec succès!')
                return redirect('client_analytics:dataset_overview', pk=dataset.pk)
        
        elif 'select' in request.POST:
            select_form = SelectDatasetForm(request.POST)
            if select_form.is_valid():
                choice_type = select_form.cleaned_data['choice_type']
                
                if choice_type == 'existing':
                    dataset = select_form.cleaned_data['existing_dataset']
                    return redirect('client_analytics:dataset_overview', pk=dataset.pk)
                
                elif choice_type == 'demo':
                    demo_key = select_form.cleaned_data['demo_dataset']
                    
                    # Check if demo dataset already exists in database
                    dataset = Dataset.objects.filter(
                        source_type='stored',
                        stored_key=demo_key
                    ).first()
                    
                    if not dataset:
                        # Create new dataset entry
                        dataset = Dataset.objects.create(
                            name=f'Demo: {demo_key}',
                            source_type='stored',
                            stored_key=demo_key
                        )
                    
                    return redirect('client_analytics:dataset_overview', pk=dataset.pk)
    
    context = {
        'upload_form': upload_form,
        'select_form': select_form,
    }
    return render(request, 'client_analytics/home.html', context)


def workflow(request):
    """Workflow explanation page"""
    return render(request, 'client_analytics/workflow.html')


def dataset_overview(request, pk):
    """Dataset overview page"""
    dataset = get_object_or_404(Dataset, pk=pk)
    
    # Load dataframe
    df = dataset_io.load_dataset_df(dataset)
    
    if df is None:
        messages.error(request, 'Erreur lors du chargement du dataset')
        return redirect('client_analytics:home')
    
    # Get dataset info
    info = profiling.get_dataset_info(df)
    missing_info = profiling.get_missing_values(df)
    numeric_summary = profiling.get_numeric_summary(df)
    column_types = profiling.get_column_types(df)
    
    # Convert dataframe head to HTML
    df_head_html = df.head(10).to_html(classes='table table-striped table-sm', index=False)
    
    # Convert numeric summary to HTML
    numeric_summary_html = None
    if numeric_summary is not None:
        numeric_summary_html = numeric_summary.to_html(classes='table table-striped table-sm')
    
    context = {
        'dataset': dataset,
        'info': info,
        'missing_info': missing_info,
        'df_head_html': df_head_html,
        'numeric_summary_html': numeric_summary_html,
        'column_types': column_types,
    }
    return render(request, 'client_analytics/dataset_overview.html', context)


def stats(request, pk):
    """Statistics page - High Tech 2024 Analytics COMPLET"""
    dataset = get_object_or_404(Dataset, pk=pk)
    
    # Load dataframe
    df = dataset_io.load_dataset_df(dataset)
    
    if df is None:
        messages.error(request, 'Erreur lors du chargement du dataset')
        return redirect('client_analytics:home')
    
    # Générer toutes les analyses statistiques COMPLÈTES
    print("🔄 Génération des analyses complètes...")
    
    # 1. Analyse statistique complète
    stat_analytics = stats_complete.generate_complete_statistics(df)
    
    # 2. Analyse temporelle complète
    temp_analytics = temporal_analysis.generate_temporal_analysis(df)
    
    # Fusionner les résultats
    all_results = {**stat_analytics.get('results', {}), **temp_analytics.get('results', {})}
    all_graphs = {**stat_analytics.get('graphs', {}), **temp_analytics.get('graphs', {})}
    all_kpis = stat_analytics.get('kpis', {})
    
    context = {
        'dataset': dataset,
        'results': all_results,
        'graphs': all_graphs,
        'kpis': all_kpis,
    }
    return render(request, 'client_analytics/stats.html', context)


def modeling(request, pk):
    """Machine learning modeling page"""
    dataset = get_object_or_404(Dataset, pk=pk)
    
    # Load dataframe
    df = dataset_io.load_dataset_df(dataset)
    
    if df is None:
        messages.error(request, 'Erreur lors du chargement du dataset')
        return redirect('client_analytics:home')
    
    results = None
    
    if request.method == 'POST':
        target_column = request.POST.get('target_column')
        feature_columns = request.POST.getlist('feature_columns')
        task_type = request.POST.get('task_type')
        model_type = request.POST.get('model_type')
        
        if not target_column or not feature_columns:
            messages.error(request, 'Veuillez sélectionner une variable cible et des features')
        else:
            # Train model
            results = modeling.train_model(
                df, target_column, feature_columns, model_type, task_type
            )
            
            if results['success']:
                messages.success(request, 'Modèle entraîné avec succès!')
            else:
                messages.error(request, f'Erreur: {results["error"]}')
    
    # Get columns for form
    all_columns = list(df.columns)
    
    context = {
        'dataset': dataset,
        'all_columns': all_columns,
        'results': results,
    }
    return render(request, 'client_analytics/modeling.html', context)


def clustering(request, pk):
    """Clustering page"""
    dataset = get_object_or_404(Dataset, pk=pk)
    
    # Load dataframe
    df = dataset_io.load_dataset_df(dataset)
    
    if df is None:
        messages.error(request, 'Erreur lors du chargement du dataset')
        return redirect('client_analytics:home')
    
    # Get numeric columns
    column_types = profiling.get_column_types(df)
    numeric_columns = column_types['numeric']
    
    results = None
    
    if request.method == 'POST':
        feature_columns = request.POST.getlist('feature_columns')
        n_clusters = int(request.POST.get('n_clusters', 3))
        standardize = request.POST.get('standardize') == 'on'
        
        if not feature_columns:
            messages.error(request, 'Veuillez sélectionner au moins une variable')
        else:
            # Perform clustering
            results = clustering.perform_clustering(
                df, feature_columns, n_clusters, standardize
            )
            
            if results['success']:
                # Store results in session for export
                request.session['clustering_results'] = {
                    'dataset_pk': pk,
                    'cluster_labels': results['cluster_labels'],
                    'valid_indices': results['valid_indices'],
                }
                messages.success(request, 'Clustering effectué avec succès!')
            else:
                messages.error(request, f'Erreur: {results["error"]}')
    
    context = {
        'dataset': dataset,
        'numeric_columns': numeric_columns,
        'results': results,
    }
    return render(request, 'client_analytics/clustering.html', context)


def clustering_export(request, pk):
    """Export clustering results to CSV"""
    dataset = get_object_or_404(Dataset, pk=pk)
    
    # Get clustering results from session
    clustering_results = request.session.get('clustering_results')
    
    if not clustering_results or clustering_results['dataset_pk'] != pk:
        messages.error(request, 'Aucun résultat de clustering trouvé. Veuillez effectuer un clustering d\'abord.')
        return redirect('client_analytics:clustering', pk=pk)
    
    # Load dataframe
    df = dataset_io.load_dataset_df(dataset)
    
    if df is None:
        messages.error(request, 'Erreur lors du chargement du dataset')
        return redirect('client_analytics:home')
    
    # Add cluster labels to dataframe
    df_export = clustering.export_clustering_results(
        df,
        clustering_results['cluster_labels'],
        clustering_results['valid_indices']
    )
    
    # Create CSV response
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{dataset.name}_clustering.csv"'
    
    df_export.to_csv(response, index=False)
    
    return response
