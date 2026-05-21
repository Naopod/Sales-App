"""
Visualisations pour le sous-onglet GÉOGRAPHIQUE
"""
import json
import uuid

import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd

# Mapping ISO alpha-2 → alpha-3 for Plotly choropleth
_ALPHA2_TO_ALPHA3 = {
    'AF': 'AFG', 'AL': 'ALB', 'DZ': 'DZA', 'AD': 'AND', 'AO': 'AGO',
    'AR': 'ARG', 'AM': 'ARM', 'AU': 'AUS', 'AT': 'AUT', 'AZ': 'AZE',
    'BS': 'BHS', 'BH': 'BHR', 'BD': 'BGD', 'BY': 'BLR', 'BE': 'BEL',
    'BZ': 'BLZ', 'BJ': 'BEN', 'BT': 'BTN', 'BO': 'BOL', 'BA': 'BIH',
    'BW': 'BWA', 'BR': 'BRA', 'BN': 'BRN', 'BG': 'BGR', 'BF': 'BFA',
    'BI': 'BDI', 'KH': 'KHM', 'CM': 'CMR', 'CA': 'CAN', 'CF': 'CAF',
    'TD': 'TCD', 'CL': 'CHL', 'CN': 'CHN', 'CO': 'COL', 'KM': 'COM',
    'CG': 'COG', 'CD': 'COD', 'CR': 'CRI', 'HR': 'HRV', 'CU': 'CUB',
    'CY': 'CYP', 'CZ': 'CZE', 'DK': 'DNK', 'DJ': 'DJI', 'DO': 'DOM',
    'EC': 'ECU', 'EG': 'EGY', 'SV': 'SLV', 'GQ': 'GNQ', 'ER': 'ERI',
    'EE': 'EST', 'ET': 'ETH', 'FJ': 'FJI', 'FI': 'FIN', 'FR': 'FRA',
    'GA': 'GAB', 'GM': 'GMB', 'GE': 'GEO', 'DE': 'DEU', 'GH': 'GHA',
    'GR': 'GRC', 'GT': 'GTM', 'GN': 'GIN', 'GW': 'GNB', 'GY': 'GUY',
    'HT': 'HTI', 'HN': 'HND', 'HU': 'HUN', 'IS': 'ISL', 'IN': 'IND',
    'ID': 'IDN', 'IR': 'IRN', 'IQ': 'IRQ', 'IE': 'IRL', 'IL': 'ISR',
    'IT': 'ITA', 'JM': 'JAM', 'JP': 'JPN', 'JO': 'JOR', 'KZ': 'KAZ',
    'KE': 'KEN', 'KP': 'PRK', 'KR': 'KOR', 'KW': 'KWT', 'KG': 'KGZ',
    'LA': 'LAO', 'LV': 'LVA', 'LB': 'LBN', 'LS': 'LSO', 'LR': 'LBR',
    'LY': 'LBY', 'LI': 'LIE', 'LT': 'LTU', 'LU': 'LUX', 'MG': 'MDG',
    'MW': 'MWI', 'MY': 'MYS', 'MV': 'MDV', 'ML': 'MLI', 'MT': 'MLT',
    'MR': 'MRT', 'MU': 'MUS', 'MX': 'MEX', 'MD': 'MDA', 'MC': 'MCO',
    'MN': 'MNG', 'ME': 'MNE', 'MA': 'MAR', 'MZ': 'MOZ', 'MM': 'MMR',
    'NA': 'NAM', 'NP': 'NPL', 'NL': 'NLD', 'NZ': 'NZL', 'NI': 'NIC',
    'NE': 'NER', 'NG': 'NGA', 'MK': 'MKD', 'NO': 'NOR', 'OM': 'OMN',
    'PK': 'PAK', 'PA': 'PAN', 'PG': 'PNG', 'PY': 'PRY', 'PE': 'PER',
    'PH': 'PHL', 'PL': 'POL', 'PT': 'PRT', 'QA': 'QAT', 'RO': 'ROU',
    'RU': 'RUS', 'RW': 'RWA', 'SA': 'SAU', 'SN': 'SEN', 'RS': 'SRB',
    'SL': 'SLE', 'SG': 'SGP', 'SK': 'SVK', 'SI': 'SVN', 'SO': 'SOM',
    'ZA': 'ZAF', 'ES': 'ESP', 'LK': 'LKA', 'SD': 'SDN', 'SR': 'SUR',
    'SZ': 'SWZ', 'SE': 'SWE', 'CH': 'CHE', 'SY': 'SYR', 'TW': 'TWN',
    'TJ': 'TJK', 'TZ': 'TZA', 'TH': 'THA', 'TL': 'TLS', 'TG': 'TGO',
    'TT': 'TTO', 'TN': 'TUN', 'TR': 'TUR', 'TM': 'TKM', 'UG': 'UGA',
    'UA': 'UKR', 'AE': 'ARE', 'GB': 'GBR', 'US': 'USA', 'UY': 'URY',
    'UZ': 'UZB', 'VE': 'VEN', 'VN': 'VNM', 'YE': 'YEM', 'ZM': 'ZMB',
    'ZW': 'ZWE',
}

# Human-readable country names for hover
_ALPHA2_TO_NAME = {
    'FR': 'France', 'BE': 'Belgique', 'DE': 'Allemagne', 'NL': 'Pays-Bas',
    'LU': 'Luxembourg', 'GB': 'Royaume-Uni', 'DK': 'Danemark', 'SE': 'Suède',
    'NO': 'Norvège', 'IE': 'Irlande', 'ES': 'Espagne', 'IT': 'Italie',
    'PT': 'Portugal', 'GR': 'Grèce', 'PL': 'Pologne', 'CZ': 'Tchéquie',
    'AT': 'Autriche', 'CH': 'Suisse', 'HU': 'Hongrie', 'SK': 'Slovaquie',
    'RO': 'Roumanie', 'HR': 'Croatie', 'BG': 'Bulgarie', 'RS': 'Serbie',
    'MK': 'Macédoine', 'LT': 'Lituanie', 'US': 'États-Unis', 'CA': 'Canada',
    'AU': 'Australie', 'JP': 'Japon', 'CN': 'Chine', 'BR': 'Brésil',
    'IN': 'Inde', 'RU': 'Russie', 'MX': 'Mexique', 'KR': 'Corée du Sud',
    'SG': 'Singapour', 'ZA': 'Afrique du Sud', 'AR': 'Argentine',
    'SA': 'Arabie Saoudite', 'AE': 'Émirats Arabes Unis', 'TR': 'Turquie',
    'IL': 'Israël', 'MA': 'Maroc', 'TN': 'Tunisie', 'EG': 'Égypte',
    'NG': 'Nigéria', 'KE': 'Kenya', 'GH': 'Ghana',
}

_COUNTRY_COORDS = {
    'FR': (46.2276, 2.2137), 'BE': (50.5039, 4.4699),
    'DE': (51.1657, 10.4515), 'NL': (52.1326, 5.2913),
    'LU': (49.8153, 6.1296), 'GB': (55.3781, -3.4360),
    'DK': (56.2639, 9.5018), 'SE': (60.1282, 18.6435),
    'NO': (60.4720, 8.4689), 'IE': (53.1424, -7.6921),
    'ES': (40.4637, -3.7492), 'IT': (41.8719, 12.5674),
    'PT': (39.3999, -8.2245), 'GR': (39.0742, 21.8243),
    'PL': (51.9194, 19.1451), 'CZ': (49.8175, 15.4730),
    'AT': (47.5162, 14.5501), 'CH': (46.8182, 8.2275),
    'HU': (47.1625, 19.5033), 'SK': (48.6690, 19.6990),
    'RO': (45.9432, 24.9668), 'HR': (45.1000, 15.2000),
    'BG': (42.7339, 25.4858), 'RS': (44.0165, 21.0059),
    'MK': (41.6086, 21.7453), 'LT': (55.1694, 23.8813),
    'US': (37.0902, -95.7129), 'CA': (56.1304, -106.3468),
    'AU': (-25.2744, 133.7751), 'JP': (36.2048, 138.2529),
    'CN': (35.8617, 104.1954), 'BR': (-14.2350, -51.9253),
    'IN': (20.5937, 78.9629), 'RU': (61.5240, 105.3188),
    'MX': (23.6345, -102.5528), 'KR': (35.9078, 127.7669),
    'SG': (1.3521, 103.8198), 'ZA': (-30.5595, 22.9375),
    'AR': (-38.4161, -63.6167), 'SA': (23.8859, 45.0792),
    'AE': (23.4241, 53.8478), 'TR': (38.9637, 35.2433),
    'IL': (31.0461, 34.8516), 'MA': (31.7917, -7.0926),
    'TN': (33.8869, 9.5375), 'EG': (26.8206, 30.8025),
    'NG': (9.0820, 8.6753), 'KE': (-0.0236, 37.9062),
    'GH': (7.9465, -1.0232),
}


def _make_responsive(fig) -> go.Figure:
    """Makes a Plotly figure responsive."""
    fig.update_layout(autosize=True, width=None, margin=dict(l=40, r=20, t=60, b=40))
    return fig


def _to_html_responsive(fig) -> str:
    """Converts a Plotly figure to responsive HTML."""
    fig = _make_responsive(fig)
    return fig.to_html(full_html=False, include_plotlyjs=False, config={'responsive': True})


def _get_country_display_name(code: str) -> str:
    """Returns a human-readable country name from ISO alpha-2 code."""
    return _ALPHA2_TO_NAME.get(code, code)


def create_leaflet_map(stats_pays: pd.DataFrame) -> str:
    """
    Creates a Leaflet marker map for country performance.

    Circle size follows country revenue. Popup details expose CA, share,
    score, clients and classification.
    """
    if stats_pays is None or len(stats_pays) == 0:
        return None

    try:
        df = stats_pays.copy()
        if df.index.name in ('Country', 'Pays') or df.index.name is None:
            df = df.reset_index()
            first_col = df.columns[0]
            df = df.rename(columns={first_col: 'code'})
        elif 'Pays' in df.columns:
            df = df.rename(columns={'Pays': 'code'})
        elif 'Country' in df.columns:
            df = df.rename(columns={'Country': 'code'})
        else:
            return None

        records = []
        for _, row in df.iterrows():
            code = str(row.get('code', '')).upper()
            coords = _COUNTRY_COORDS.get(code)
            if not coords:
                continue
            records.append({
                'code': code,
                'country': _get_country_display_name(code),
                'lat': coords[0],
                'lng': coords[1],
                'zone': row.get('Zone', 'N/A'),
                'classification': row.get('Classification', 'N/A'),
                'ca_total': float(row.get('CA_Total', 0) or 0),
                'part_pct': float(row.get('Part_Pct', 0) or 0),
                'score_global': float(row.get('Score_Global', 0) or 0),
                'nb_clients': int(row.get('Nb_Clients', 0) or 0),
                'panier_moyen': float(row.get('Panier_Moyen', 0) or 0),
            })

        if not records:
            return None

        map_id = f"geoLeafletMap_{uuid.uuid4().hex}"
        data_json = json.dumps(records, ensure_ascii=False).replace("</", "<\\/")

        return f"""
<div class="geo-leaflet-map" id="{map_id}" style="height: 520px; min-height: 420px; width: 100%;"></div>
<script>
(function() {{
    const mapEl = document.getElementById("{map_id}");
    const points = {data_json};
    if (!mapEl || mapEl.dataset.initialized === "true") return;
    if (!window.L) {{
        mapEl.innerHTML = '<div class="alert alert-warning m-3">La carte Leaflet n\\'est pas encore disponible.</div>';
        return;
    }}
    mapEl.dataset.initialized = "true";

    const escapeHtml = function(value) {{
        return String(value ?? '').replace(/[&<>"']/g, function(char) {{
            return ({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}})[char];
        }});
    }};
    const formatEuro = function(value) {{
        return Number(value || 0).toLocaleString('fr-FR', {{ maximumFractionDigits: 0 }}) + ' €';
    }};
    const colorFor = function(classification) {{
        if (classification === 'Excellence') return '#10b981';
        if (classification === 'Performant') return '#2563eb';
        if (classification === 'Moyen') return '#f59e0b';
        return '#ef4444';
    }};

    const map = L.map(mapEl, {{ scrollWheelZoom: false, worldCopyJump: true }});
    L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
        maxZoom: 7,
        attribution: '&copy; OpenStreetMap contributors'
    }}).addTo(map);

    const maxCa = Math.max(...points.map(point => Number(point.ca_total) || 0), 1);
    const bounds = [];
    points.forEach(function(point) {{
        const ca = Number(point.ca_total) || 0;
        const radius = 7 + Math.sqrt(ca / maxCa) * 28;
        const color = colorFor(point.classification);
        const marker = L.circleMarker([point.lat, point.lng], {{
            radius: radius,
            color: color,
            weight: 2,
            fillColor: color,
            fillOpacity: 0.42
        }}).addTo(map);

        marker.bindPopup(`
            <div class="geo-leaflet-popup">
                <strong>${{escapeHtml(point.country)}} (${{escapeHtml(point.code)}})</strong><br>
                Zone: ${{escapeHtml(point.zone)}}<br>
                Classification: <strong>${{escapeHtml(point.classification)}}</strong><br>
                CA total: <strong>${{formatEuro(point.ca_total)}}</strong><br>
                Part du CA: ${{Number(point.part_pct || 0).toFixed(1)}}%<br>
                Score global: ${{Number(point.score_global || 0).toFixed(1)}}/100<br>
                Clients: ${{Number(point.nb_clients || 0).toLocaleString('fr-FR')}}<br>
                Panier moyen: ${{formatEuro(point.panier_moyen)}}
            </div>
        `);
        bounds.push([point.lat, point.lng]);
    }});

    if (bounds.length) {{
        map.fitBounds(bounds, {{ padding: [32, 32], maxZoom: 5 }});
    }} else {{
        map.setView([46.5, 2.5], 4);
    }}
    setTimeout(function() {{ map.invalidateSize(); }}, 150);
}})();
</script>
"""
    except Exception as e:
        print(f"   ⚠️ Erreur carte Leaflet géographique: {e}")
        return None


def create_world_map(stats_pays: pd.DataFrame) -> str:
    """
    Creates an interactive world choropleth map with selectable metrics.

    The map supports switching between CA, Score Global, Nombre de Clients,
    Panier Moyen and Part CA via a dropdown button group. Hover shows all KPIs.

    Args:
        stats_pays: DataFrame with country code as index and columns:
                    CA_Total, Score_Global, Nb_Clients, Panier_Moyen,
                    Part_Pct, Classification, Zone, etc.

    Returns:
        str: Responsive HTML of the Plotly figure, or None on error.
    """
    if stats_pays is None or len(stats_pays) == 0:
        return None

    try:
        # Work with a copy; ensure country code is available as a column
        df = stats_pays.copy()
        if df.index.name in ('Country', 'Pays') or df.index.name is None:
            df = df.reset_index()
            # After reset, rename whatever came from index to 'code'
            first_col = df.columns[0]
            df = df.rename(columns={first_col: 'code'})
        elif 'Pays' in df.columns:
            df = df.rename(columns={'Pays': 'code'})
        elif 'Country' in df.columns:
            df = df.rename(columns={'Country': 'code'})
        else:
            return None

        # Map to ISO alpha-3
        df['iso3'] = df['code'].map(_ALPHA2_TO_ALPHA3)
        df['country_name'] = df['code'].apply(_get_country_display_name)
        df = df.dropna(subset=['iso3'])

        if df.empty:
            return None

        # Classification colour for marker border
        classif_color_map = {
            'Excellence': '#10b981',
            'Performant': '#3b82f6',
            'Moyen': '#f59e0b',
            'À Développer': '#ef4444',
        }

        # Build rich hover text
        def _hover(row) -> str:
            name = row.get('country_name', row.get('code', ''))
            lines = [
                f"<b>{name}</b>",
                f"Zone: {row.get('Zone', 'N/A')}",
                f"Classification: <b>{row.get('Classification', 'N/A')}</b>",
                "─────────────────",
                f"CA Total: <b>{row.get('CA_Total', 0):,.0f} €</b>",
                f"Part du CA: {row.get('Part_Pct', 0):.1f}%",
                f"Score Global: <b>{row.get('Score_Global', 0):.1f}/100</b>",
                "─────────────────",
                f"Clients: {int(row.get('Nb_Clients', 0))}",
                f"Commandes: {int(row.get('Nb_Commandes', 0))}",
                f"Panier Moyen: {row.get('Panier_Moyen', 0):,.0f} €",
                f"CA / Client: {row.get('CA_par_Client', 0):,.0f} €",
            ]
            return "<br>".join(lines)

        df['hover'] = df.apply(_hover, axis=1)

        # ── Metric definitions: (label, column, colorscale, format_suffix) ──
        metric_defs = [
            ("CA Total (€)",          "CA_Total",      "Blues",   "€"),
            ("Score de Performance",  "Score_Global",  "RdYlGn",  "/100"),
            ("Nombre de Clients",     "Nb_Clients",    "Oranges", ""),
            ("Panier Moyen (€)",      "Panier_Moyen",  "Purples", "€"),
            ("Part du CA (%)",        "Part_Pct",      "YlOrRd",  "%"),
        ]
        # Keep only metrics present in the DataFrame
        metric_defs = [(lbl, col, cs, sfx) for lbl, col, cs, sfx in metric_defs if col in df.columns]

        if not metric_defs:
            return None

        traces = []
        for i, (label, col, colorscale, suffix) in enumerate(metric_defs):
            traces.append(go.Choropleth(
                locations=df['iso3'],
                z=df[col],
                text=df['hover'],
                hoverinfo='text',
                colorscale=colorscale,
                reversescale=(col == 'Nb_Clients'),
                autocolorscale=False,
                colorbar=dict(
                    title=dict(text=label, side='right'),
                    thickness=15,
                    len=0.7,
                ),
                marker_line_color='white',
                marker_line_width=0.5,
                visible=(i == 0),
                name=label,
                zmin=df[col].min(),
                zmax=df[col].max(),
            ))

        # Dropdown buttons
        n = len(metric_defs)
        buttons = []
        for i, (label, col, colorscale, suffix) in enumerate(metric_defs):
            buttons.append(dict(
                label=label,
                method='update',
                args=[
                    {'visible': [j == i for j in range(n)]},
                    {'title': {'text': f"🌍 Carte Mondiale — {label}",
                               'font': {'size': 18}}},
                ],
            ))

        fig = go.Figure(data=traces)
        fig.update_layout(
            title=dict(
                text=f"🌍 Carte Mondiale — {metric_defs[0][0]}",
                font=dict(size=18),
                x=0.5,
                xanchor='center',
            ),
            geo=dict(
                showframe=False,
                showcoastlines=True,
                coastlinecolor='rgba(100,100,100,0.5)',
                projection_type='natural earth',
                showland=True,
                landcolor='#f0f0f0',
                showocean=True,
                oceancolor='#d4e6f1',
                showlakes=True,
                lakecolor='#d4e6f1',
                showcountries=True,
                countrycolor='rgba(180,180,180,0.5)',
                bgcolor='rgba(0,0,0,0)',
            ),
            height=560,
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            updatemenus=[dict(
                type='buttons',
                direction='right',
                showactive=True,
                x=0.5,
                xanchor='center',
                y=1.08,
                yanchor='top',
                bgcolor='rgba(255,255,255,0.9)',
                bordercolor='rgba(0,0,0,0.15)',
                font=dict(size=12),
                buttons=buttons,
                pad=dict(l=4, r=4, t=4, b=4),
            )],
            margin=dict(l=0, r=0, t=90, b=20),
        )

        return _to_html_responsive(fig)

    except Exception as e:
        print(f"[viz_geographic] Erreur world map: {e}")
        return None


def create_geographic_ca_chart(stats_pays: pd.DataFrame) -> str:
    """Bar chart: top 15 countries by revenue."""
    if stats_pays is None or len(stats_pays) == 0:
        return None

    try:
        top_countries = stats_pays.nlargest(15, 'CA_Total')

        color_map = {
            'Excellence': '#10b981',
            'Performant': '#3b82f6',
            'Moyen': '#f59e0b',
            'À Développer': '#ef4444',
        }
        colors = [color_map.get(c, '#6b7280') for c in top_countries.get('Classification', [])]

        # Labels: use index (country code) or 'Pays' column
        labels = (
            top_countries['Pays'].tolist()
            if 'Pays' in top_countries.columns
            else list(top_countries.index)
        )

        fig = go.Figure(data=[
            go.Bar(
                y=labels,
                x=top_countries['CA_Total'],
                orientation='h',
                marker_color=colors or '#3b82f6',
                text=top_countries['CA_Total'].apply(lambda x: f'{x:,.0f}€'),
                textposition='outside',
                hovertemplate='<b>%{y}</b><br>CA: %{x:,.0f}€<br>Classification: %{customdata}<extra></extra>',
                customdata=top_countries.get('Classification', []),
            )
        ])

        fig.update_layout(
            title="Top 15 Pays par Chiffre d'Affaires",
            xaxis_title="Chiffre d'Affaires (€)",
            yaxis_title="Pays",
            height=520,
            showlegend=False,
        )

        return _to_html_responsive(fig)

    except Exception as e:
        print(f"[viz_geographic] Erreur graphique CA: {e}")
        return None


def create_zone_performance_chart(stats_zone: pd.DataFrame) -> str:
    """Side-by-side bar chart: CA and clients per geographic zone."""
    if stats_zone is None or len(stats_zone) == 0:
        return None

    try:
        # Labels come from index or a 'Zone' column
        zone_labels = (
            stats_zone['Zone'].tolist()
            if 'Zone' in stats_zone.columns
            else list(stats_zone.index)
        )

        fig = make_subplots(
            rows=1, cols=2,
            subplot_titles=("CA par Zone", "Nombre de Clients par Zone"),
            specs=[[{"type": "bar"}, {"type": "bar"}]],
        )

        fig.add_trace(
            go.Bar(
                x=zone_labels,
                y=stats_zone['CA_Total'],
                name='CA Total',
                marker_color='#3b82f6',
                text=stats_zone['CA_Total'].apply(lambda x: f'{x:,.0f}€'),
                textposition='outside',
                hovertemplate='<b>%{x}</b><br>CA: %{y:,.0f}€<extra></extra>',
            ),
            row=1, col=1,
        )

        fig.add_trace(
            go.Bar(
                x=zone_labels,
                y=stats_zone['Nb_Clients'],
                name='Nb Clients',
                marker_color='#10b981',
                text=stats_zone['Nb_Clients'],
                textposition='outside',
                hovertemplate='<b>%{x}</b><br>Clients: %{y}<extra></extra>',
            ),
            row=1, col=2,
        )

        fig.update_xaxes(title_text="Zone", row=1, col=1)
        fig.update_xaxes(title_text="Zone", row=1, col=2)
        fig.update_yaxes(title_text="CA (€)", row=1, col=1)
        fig.update_yaxes(title_text="Nombre de Clients", row=1, col=2)
        fig.update_layout(height=460, showlegend=False)

        return _to_html_responsive(fig)

    except Exception as e:
        print(f"[viz_geographic] Erreur graphique zones: {e}")
        return None


def create_classification_chart(stats_pays: pd.DataFrame) -> str:
    """Donut chart: country count by performance classification."""
    if stats_pays is None or 'Classification' not in stats_pays.columns:
        return None

    try:
        classif_counts = stats_pays['Classification'].value_counts()

        color_map = {
            'Excellence': '#10b981',
            'Performant': '#3b82f6',
            'Moyen': '#f59e0b',
            'À Développer': '#ef4444',
        }
        colors = [color_map.get(c, '#6b7280') for c in classif_counts.index]

        fig = go.Figure(data=[
            go.Pie(
                labels=classif_counts.index,
                values=classif_counts.values,
                hole=0.4,
                marker_colors=colors,
                textinfo='label+value+percent',
                hovertemplate='<b>%{label}</b><br>Pays: %{value}<br>%{percent}<extra></extra>',
            )
        ])

        fig.update_layout(title="Répartition des Pays par Classification", height=400)
        return _to_html_responsive(fig)

    except Exception as e:
        print(f"[viz_geographic] Erreur graphique classification: {e}")
        return None


