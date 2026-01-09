"""
Service d'Analyse Temporelle Complète - High Tech 2024
Analyse temporelle avancée avec saisonnalité, tendances, STL, ARIMA
"""
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from statsmodels.tsa.seasonal import STL, seasonal_decompose
from statsmodels.tsa.stattools import adfuller, kpss
from statsmodels.tsa.arima.model import ARIMA
from sklearn.metrics import mean_absolute_percentage_error
import warnings
warnings.filterwarnings('ignore')


def generate_temporal_analysis(df):
    """
    Génère l'analyse temporelle COMPLÈTE
    - Évolution par trimestre, mois, semaine, jour
    - Décomposition STL (Tendance + Saisonnalité + Résidu)
    - Tests de stationnarité (ADF, KPSS)
    - Prévisions ARIMA
    - Heatmaps temporelles
    """
    results = {}
    graphs = {}
    
    print("📅 Génération de l'analyse temporelle complète...")
    
    # ═══════════════════════════════════════════════════════════════════
    # ÉTAPE 1 : TABLEAU DE BORD TEMPOREL COMPLET
    # ═══════════════════════════════════════════════════════════════════
    
    print("   📊 Étape 1 : Tableau de bord temporel...")
    
    # Agrégations temporelles
    if 'Quarter' in df.columns and 'Montant' in df.columns:
        agg_dict = {'Montant': 'sum'}
        if 'Quantité' in df.columns:
            agg_dict['Quantité'] = 'sum'
        if 'Cpt Client' in df.columns:
            agg_dict['Cpt Client'] = 'nunique'
        if 'N° Bon' in df.columns:
            agg_dict['N° Bon'] = 'nunique'
        
        stats_trim = df.groupby('Quarter').agg(agg_dict)
        stats_trim.columns = ['CA_Total', 'Qty_Total', 'Nb_Clients', 'Nb_Commandes']
        
        # Graphique CA Total par Trimestre
        fig1 = go.Figure(data=[
            go.Bar(
                x=stats_trim.index,
                y=stats_trim['CA_Total'],
                marker_color=['#e74c3c', '#3498db', '#2ecc71', '#f39c12'],
                text=[f"{v/1e6:.2f}M€" for v in stats_trim['CA_Total']],
                textposition='outside',
                textfont=dict(size=12, color='black', family='Arial Black')
            )
        ])
        fig1.update_layout(
            title='<b>💰 CA Total par Trimestre 2024</b>',
            xaxis_title='Trimestre',
            yaxis_title='CA (€)',
            height=500,
            template='plotly_white'
        )
        graphs['ca_par_trimestre'] = fig1.to_html(full_html=False, include_plotlyjs='cdn')
        
        # Variation trimestrielle
        variations = stats_trim['CA_Total'].pct_change() * 100
        
        fig2 = go.Figure(data=[
            go.Bar(
                x=stats_trim.index[1:],
                y=variations[1:],
                marker_color=['red' if v < 0 else 'green' for v in variations[1:]],
                text=[f"{v:+.1f}%" for v in variations[1:]],
                textposition='outside',
                textfont=dict(size=12)
            )
        ])
        fig2.update_layout(
            title='<b>📈 Variation Trimestrielle du CA (%)</b>',
            xaxis_title='Trimestre',
            yaxis_title='Variation (%)',
            height=500,
            template='plotly_white'
        )
        graphs['variation_trimestrielle'] = fig2.to_html(full_html=False, include_plotlyjs='cdn')
    
    # ═══════════════════════════════════════════════════════════════════
    # ÉTAPE 2 : ÉVOLUTION MENSUELLE DU CHIFFRE D'AFFAIRES
    # ═══════════════════════════════════════════════════════════════════
    
    print("   📅 Étape 2 : Évolution mensuelle...")
    
    if 'Date Cde' in df.columns:
        # Convertir en datetime
        df['Date Cde'] = pd.to_datetime(df['Date Cde'], errors='coerce')
        
        # CA quotidien
        daily_ca = df.groupby(df['Date Cde'].dt.date)['Montant'].sum()
        
        # CA mensuel
        monthly_ca = df.groupby(df['Date Cde'].dt.to_period('M'))['Montant'].sum()
        monthly_ca.index = monthly_ca.index.to_timestamp()
        
        # Graphique évolution mensuelle avec tendance
        fig3 = go.Figure()
        
        fig3.add_trace(go.Scatter(
            x=monthly_ca.index,
            y=monthly_ca.values,
            mode='lines+markers',
            name='CA Mensuel',
            line=dict(color='steelblue', width=3),
            marker=dict(size=10),
            text=[f"{v/1e6:.2f}M€" for v in monthly_ca.values],
            textposition='top center'
        ))
        
        # Ligne de tendance (régression linéaire)
        x_numeric = np.arange(len(monthly_ca))
        z = np.polyfit(x_numeric, monthly_ca.values, 1)
        p = np.poly1d(z)
        
        fig3.add_trace(go.Scatter(
            x=monthly_ca.index,
            y=p(x_numeric),
            mode='lines',
            name='Tendance',
            line=dict(color='red', width=2, dash='dash')
        ))
        
        fig3.update_layout(
            title='<b>📊 Évolution Mensuelle du Chiffre d\'Affaires</b>',
            xaxis_title='Mois',
            yaxis_title='CA (€)',
            height=500,
            template='plotly_white',
            hovermode='x unified'
        )
        graphs['evolution_mensuelle'] = fig3.to_html(full_html=False, include_plotlyjs='cdn')
    
    # ═══════════════════════════════════════════════════════════════════
    # ÉTAPE 3 : ANALYSES TEMPORELLES DÉTAILLÉES (Jours, Semaines)
    # ═══════════════════════════════════════════════════════════════════
    
    print("   🗓️ Étape 3 : Analyses par jour de semaine et semaine...")
    
    if 'Date Cde' in df.columns:
        df['Jour_Semaine'] = df['Date Cde'].dt.day_name()
        df['Semaine_Annee'] = df['Date Cde'].dt.isocalendar().week
        
        # CA par jour de la semaine
        jour_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        stats_jour = df.groupby('Jour_Semaine')['Montant'].agg(['sum', 'mean', 'count'])
        stats_jour = stats_jour.reindex(jour_order)
        
        fig4 = make_subplots(
            rows=1, cols=3,
            subplot_titles=('CA Total par Jour', 'Nb Ventes par Jour', 'CA Moyen par Transaction')
        )
        
        fig4.add_trace(
            go.Bar(x=stats_jour.index, y=stats_jour['sum'], marker_color='steelblue'),
            row=1, col=1
        )
        fig4.add_trace(
            go.Bar(x=stats_jour.index, y=stats_jour['count'], marker_color='indianred'),
            row=1, col=2
        )
        fig4.add_trace(
            go.Bar(x=stats_jour.index, y=stats_jour['mean'], marker_color='mediumseagreen'),
            row=1, col=3
        )
        
        fig4.update_xaxes(tickangle=-45)
        fig4.update_layout(
            title_text='<b>📅 CA Total par Jour de la Semaine</b>',
            height=500,
            template='plotly_white',
            showlegend=False
        )
        graphs['analyse_jour_semaine'] = fig4.to_html(full_html=False, include_plotlyjs='cdn')
        
        # CA par semaine de l'année
        weekly_ca = df.groupby('Semaine_Annee')['Montant'].sum()
        
        fig5 = go.Figure(data=[
            go.Scatter(
                x=weekly_ca.index,
                y=weekly_ca.values,
                mode='lines+markers',
                fill='tozeroy',
                fillcolor='rgba(70, 130, 180, 0.2)',
                line=dict(color='steelblue', width=2),
                marker=dict(size=6)
            )
        ])
        
        fig5.update_layout(
            title='<b>📊 CA Total par Semaine (52 semaines)</b>',
            xaxis_title='Semaine de l\'année',
            yaxis_title='CA (€)',
            height=500,
            template='plotly_white'
        )
        graphs['ca_par_semaine'] = fig5.to_html(full_html=False, include_plotlyjs='cdn')
    
    # ═══════════════════════════════════════════════════════════════════
    # ÉTAPE 4 : ANALYSES STATISTIQUES AVANCÉES - SÉRIES TEMPORELLES
    # ═══════════════════════════════════════════════════════════════════
    
    print("   📈 Étape 4 : Analyses STL et stationnarité...")
    
    if 'Date Cde' in df.columns:
        # Série temporelle quotidienne
        daily_ca_series = df.groupby(df['Date Cde'].dt.date)['Montant'].sum()
        daily_ca_series.index = pd.to_datetime(daily_ca_series.index)
        
        # Remplir les jours manquants
        full_range = pd.date_range(daily_ca_series.index.min(), daily_ca_series.index.max(), freq='D')
        daily_ca_series = daily_ca_series.reindex(full_range, fill_value=0)
        
        # Décomposition STL (Seasonal-Trend decomposition using LOESS)
        try:
            stl = STL(daily_ca_series, seasonal=13)  # 13 jours de saisonnalité
            result = stl.fit()
            
            fig6 = make_subplots(
                rows=4, cols=1,
                subplot_titles=(
                    '📊 Série Temporelle Originale - CA Quotidien',
                    '📈 Composante TENDANCE (STL)',
                    '🔄 Composante SAISONNIÈRE (Force: {:.1f}%)'.format(
                        (1 - result.resid.var() / result.seasonal.var()) * 100
                    ),
                    '🎲 Composante RÉSIDUELLE'
                ),
                vertical_spacing=0.08
            )
            
            # Série originale
            fig6.add_trace(
                go.Scatter(x=daily_ca_series.index, y=daily_ca_series.values,
                          mode='lines', line=dict(color='blue', width=1)),
                row=1, col=1
            )
            
            # Tendance
            fig6.add_trace(
                go.Scatter(x=result.trend.index, y=result.trend.values,
                          mode='lines', line=dict(color='red', width=2)),
                row=2, col=1
            )
            
            # Saisonnalité
            fig6.add_trace(
                go.Scatter(x=result.seasonal.index, y=result.seasonal.values,
                          mode='lines', fill='tozeroy', line=dict(color='green', width=1)),
                row=3, col=1
            )
            
            # Résidu
            fig6.add_trace(
                go.Scatter(x=result.resid.index, y=result.resid.values,
                          mode='markers', marker=dict(color='gray', size=2)),
                row=4, col=1
            )
            
            fig6.update_layout(
                height=1000,
                title_text='<b>📊 ANALYSES STATISTIQUES AVANCÉES - SÉRIES TEMPORELLES (STL)</b>',
                template='plotly_white',
                showlegend=False
            )
            graphs['stl_decomposition'] = fig6.to_html(full_html=False, include_plotlyjs='cdn')
            
            # Calcul des forces de tendance et saisonnalité
            trend_strength = (1 - result.resid.var() / result.trend.var()) * 100
            seasonal_strength = (1 - result.resid.var() / result.seasonal.var()) * 100
            
            results['stl_trend_strength'] = f"{trend_strength:.1f}%"
            results['stl_seasonal_strength'] = f"{seasonal_strength:.1f}%"
            
        except Exception as e:
            print(f"      ⚠️ Erreur STL : {e}")
            graphs['stl_decomposition'] = f"<div class='alert alert-warning'>Décomposition STL non disponible : {e}</div>"
        
        # Tests de stationnarité
        print("      • Tests de stationnarité (ADF, KPSS)...")
        
        # Test ADF (Augmented Dickey-Fuller)
        adf_result = adfuller(daily_ca_series.dropna())
        
        # Test KPSS
        kpss_result = kpss(daily_ca_series.dropna(), regression='c')
        
        stationarity_table = pd.DataFrame({
            'Test': ['ADF (Augmented Dickey-Fuller)', 'KPSS'],
            'Statistique': [f"{adf_result[0]:.4f}", f"{kpss_result[0]:.4f}"],
            'p-value': [f"{adf_result[1]:.4f}", f"{kpss_result[1]:.4f}"],
            'Résultat': [
                '✅ Stationnaire' if adf_result[1] < 0.05 else '❌ Non stationnaire',
                '✅ Stationnaire' if kpss_result[1] > 0.05 else '❌ Non stationnaire'
            ],
            'Interprétation': [
                'La série est stationnaire (tendance stable)' if adf_result[1] < 0.05 
                    else 'La série est non stationnaire (tendance présente)',
                'La série est stationnaire autour d\'une constante' if kpss_result[1] > 0.05
                    else 'La série a une tendance déterministe'
            ]
        })
        
        results['stationarity_tests'] = stationarity_table.to_html(
            classes='table table-striped table-hover',
            index=False,
            border=0,
            escape=False
        )
    
    # ═══════════════════════════════════════════════════════════════════
    # ÉTAPE 5 : PRÉVISIONS ARIMA
    # ═══════════════════════════════════════════════════════════════════
    
    print("   🔮 Étape 5 : Prévisions ARIMA...")
    
    if 'Date Cde' in df.columns and len(daily_ca_series) > 30:
        try:
            # Utiliser les 80% des données pour l'entraînement
            train_size = int(len(daily_ca_series) * 0.8)
            train, test = daily_ca_series[:train_size], daily_ca_series[train_size:]
            
            # Modèle ARIMA(1,1,1)
            model = ARIMA(train, order=(1, 1, 1))
            model_fit = model.fit()
            
            # Prévisions
            forecast = model_fit.forecast(steps=len(test))
            
            # Métriques
            mape = mean_absolute_percentage_error(test, forecast) * 100
            rmse = np.sqrt(((test - forecast) ** 2).mean())
            
            results['arima_mape'] = f"{mape:.2f}%"
            results['arima_rmse'] = f"{rmse:,.2f}€"
            
            # Graphique prévisions
            fig7 = go.Figure()
            
            fig7.add_trace(go.Scatter(
                x=train.index,
                y=train.values,
                mode='lines',
                name='Données d\'entraînement',
                line=dict(color='blue', width=2)
            ))
            
            fig7.add_trace(go.Scatter(
                x=test.index,
                y=test.values,
                mode='lines',
                name='Valeurs Réelles (Test)',
                line=dict(color='green', width=2)
            ))
            
            fig7.add_trace(go.Scatter(
                x=test.index,
                y=forecast,
                mode='lines',
                name='Prévisions ARIMA(1,1,1)',
                line=dict(color='red', width=2, dash='dash')
            ))
            
            fig7.update_layout(
                title=f'<b>🔮 Prévisions ARIMA - MAPE: {mape:.2f}% | RMSE: {rmse:,.0f}€</b>',
                xaxis_title='Date',
                yaxis_title='CA (€)',
                height=600,
                template='plotly_white',
                hovermode='x unified'
            )
            graphs['arima_forecast'] = fig7.to_html(full_html=False, include_plotlyjs='cdn')
            
        except Exception as e:
            print(f"      ⚠️ Erreur ARIMA : {e}")
            graphs['arima_forecast'] = f"<div class='alert alert-warning'>Prévisions ARIMA non disponibles : {e}</div>"
    
    # ═══════════════════════════════════════════════════════════════════
    # ÉTAPE 6 : HEATMAP TEMPORELLE (Mois × Trimestre)
    # ═══════════════════════════════════════════════════════════════════
    
    print("   🔥 Étape 6 : Heatmap CA mensuel par trimestre...")
    
    if 'Date Cde' in df.columns and 'Quarter' in df.columns:
        df['Mois'] = df['Date Cde'].dt.month
        
        heatmap_data = df.pivot_table(
            values='Montant',
            index='Quarter',
            columns='Mois',
            aggfunc='sum',
            fill_value=0
        )
        
        fig8 = go.Figure(data=go.Heatmap(
            z=heatmap_data.values,
            x=[f"Mois {m}" for m in heatmap_data.columns],
            y=heatmap_data.index,
            text=np.round(heatmap_data.values, 0),
            texttemplate='%{text:,.0f}€',
            textfont={"size": 10, "color": "white"},
            colorscale='Blues',
            colorbar=dict(title="CA (€)")
        ))
        
        fig8.update_layout(
            title='<b>🔥 Heatmap: CA Mensuel par Trimestre</b>',
            xaxis_title='Mois',
            yaxis_title='Trimestre',
            height=500,
            template='plotly_white'
        )
        graphs['heatmap_ca_mensuel'] = fig8.to_html(full_html=False, include_plotlyjs='cdn')
    
    # ═══════════════════════════════════════════════════════════════════
    # SYNTHÈSE ANALYSE TEMPORELLE
    # ═══════════════════════════════════════════════════════════════════
    
    print("   📝 Génération de la synthèse temporelle...")
    
    synthese_temporelle = """
    <div class="card border-success">
        <div class="card-header bg-success text-white">
            <h5 class="mb-0">📝 SYNTHÈSE DE L'ANALYSE TEMPORELLE</h5>
        </div>
        <div class="card-body">
            <h6 class="text-success">🔍 Principaux constats temporels :</h6>
            <ul>
                <li><strong>Évolution trimestrielle :</strong> Variations saisonnières identifiées</li>
                <li><strong>Tendance générale :</strong> Analyse de la trajectoire annuelle</li>
                <li><strong>Saisonnalité :</strong> Composante saisonnière détectée via STL</li>
                <li><strong>Stationnarité :</strong> Tests ADF et KPSS effectués</li>
            </ul>
            
            <h6 class="text-success mt-3">📊 Décomposition STL :</h6>
            <ul>
                <li><strong>Tendance :</strong> Composante long terme du CA</li>
                <li><strong>Saisonnalité :</strong> Variations cycliques régulières</li>
                <li><strong>Résidu :</strong> Variations non expliquées (événements ponctuels)</li>
            </ul>
            
            <h6 class="text-success mt-3">💡 Recommandations :</h6>
            <ul>
                <li>Anticiper les pics saisonniers pour optimiser les stocks</li>
                <li>Adapter les campagnes marketing aux périodes fortes</li>
                <li>Surveiller les anomalies dans les résidus</li>
                <li>Utiliser les prévisions ARIMA pour la planification</li>
            </ul>
        </div>
    </div>
    """
    
    results['synthese_temporelle'] = synthese_temporelle
    
    print("✅ Analyse temporelle complète générée !")
    
    return {
        'results': results,
        'graphs': graphs
    }
