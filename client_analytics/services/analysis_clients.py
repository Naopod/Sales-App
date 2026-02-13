"""
Service pour le sous-onglet ANALYSE CLIENTS
Analyse de la segmentation client, RFM, concentration
"""
import pandas as pd
import numpy as np


def _pick_col(df: pd.DataFrame, candidates) -> str | None:
    """Retourne le 1er nom de colonne existant dans df parmi candidates."""
    if df is None or df.empty:
        return None
    for col in candidates or []:
        if col in df.columns:
            return col
    return None


def get_client_options(df: pd.DataFrame, max_clients: int = 500) -> list[dict]:
    """Construit la liste des clients pour un <select> (triée par CA desc).

    Retourne une liste de dicts sérialisables: [{'value': '...', 'label': '...'}]
    """
    if df is None or df.empty:
        return []

    client_col = _pick_col(df, ['Cpt Client', 'Compte Client', 'Client', 'Code Client'])
    amount_col = _pick_col(df, ['Montant', 'CA', 'CA Net', 'Chiffre d\'Affaires'])
    if not client_col or not amount_col:
        return []

    title_col = _pick_col(df, ['Intitulé', 'Intitule', 'Intitulé Client', 'Nom Client', 'Raison Sociale'])

    df2 = df[[client_col, amount_col] + ([title_col] if title_col else [])].copy()
    df2[amount_col] = pd.to_numeric(df2[amount_col], errors='coerce')

    agg = df2.groupby(client_col, dropna=False)[amount_col].sum().sort_values(ascending=False)
    top_ids = agg.head(max_clients).index

    labels = {}
    if title_col:
        # Pour éviter des labels vides, on prend le premier intitulé non-null par client
        tmp = (
            df2[[client_col, title_col]]
            .dropna(subset=[client_col])
            .dropna(subset=[title_col])
            .groupby(client_col)[title_col]
            .first()
        )
        labels = tmp.to_dict()

    options = []
    for client_id in top_ids:
        value = '' if pd.isna(client_id) else str(client_id)
        if not value:
            continue
        if title_col and client_id in labels and labels.get(client_id) not in [None, '', 'nan']:
            label = f"{value} — {labels.get(client_id)}"
        else:
            label = value
        options.append({'value': value, 'label': label})

    return options


def analyze_client_portfolio_full(
    df: pd.DataFrame,
    client_id: str,
    time_granularity: str = 'month',
    top_n_families: int = 8,
    top_n_products: int = 10,
) -> dict:
    """Analyse complète d'un client (Client 360), robuste aux colonnes manquantes.

    Tous les objets retournés sont sérialisables (dict/list/str/float/int/None).
    """

    def _safe_float(x):
        try:
            if x is None or (isinstance(x, float) and np.isnan(x)):
                return None
            if pd.isna(x):
                return None
            return float(x)
        except Exception:
            return None

    def _safe_int(x):
        try:
            if x is None or pd.isna(x):
                return None
            return int(x)
        except Exception:
            return None

    def _to_datetime(s: pd.Series):
        try:
            return pd.to_datetime(s, errors='coerce', dayfirst=True, infer_datetime_format=True)
        except Exception:
            return pd.to_datetime(s, errors='coerce')

    def _weighted_mean(values: pd.Series, weights: pd.Series):
        v = pd.to_numeric(values, errors='coerce')
        w = pd.to_numeric(weights, errors='coerce')
        mask = v.notna() & w.notna() & (w > 0)
        if mask.sum() == 0:
            return None
        return float((v[mask] * w[mask]).sum() / w[mask].sum())

    portfolio = {
        'client_id': str(client_id) if client_id is not None else None,
        'kpis': {},
        'tables': {
            'families_portfolio': [],
            'top_products': [],
            'lead_time_by_product': [],
            'monthly_summary': [],
        },
        'graphs': {},
        'alerts': [],
        'meta': {},
    }

    tg = str(time_granularity or 'month').lower().strip()
    if tg in ['fiscal', 'fiscal_year', 'fiscale', 'annuel', 'annuelle']:
        tg = 'year'
    if tg not in ['month', 'quarter', 'year']:
        tg = 'month'

    period_label = 'Mois'
    period_unit = 'mois'
    period_adjective = 'mensuel'
    if tg == 'quarter':
        period_label = 'Trimestre'
        period_unit = 'trimestre'
        period_adjective = 'trimestriel'
    elif tg == 'year':
        period_label = 'Année fiscale'
        period_unit = 'année'
        period_adjective = 'annuel'

    if df is None or df.empty:
        portfolio['error'] = 'Dataset vide'
        return portfolio

    client_col = _pick_col(df, ['Cpt Client', 'Compte Client', 'Client', 'Code Client'])
    if not client_col:
        portfolio['error'] = 'Colonne client introuvable'
        return portfolio

    # Date: priorité demandée
    date_col = _pick_col(df, ['Date Cde', 'Date Cde.', 'Date Commande', 'Date Fact.', 'Date_Ref'])
    amount_col = _pick_col(df, ['Montant', 'CA', 'CA Net', 'Chiffre d\'Affaires'])
    order_col = 'N° Bon' if 'N° Bon' in df.columns else _pick_col(df, ['No Bon', 'N Bon', 'Bon', 'N° Commande', 'Commande'])
    qty_col = _pick_col(df, ['Quantité', 'Quantite', 'Qte', 'Qté', 'Quantity'])
    pu_col = _pick_col(df, ['PU Net', 'PU_net', 'PU_NET', 'Prix Unitaire Net', 'PU Net (€)'])
    family_col = _pick_col(df, ['Famille', 'Famille Produit', 'Famille article', 'Famille_Produit'])
    product_col = _pick_col(df, ['Code Recette', 'Libelle 1', 'Libellé 1', 'Produit', 'Article', 'Désignation'])
    country_col = _pick_col(df, ['Country', 'Pays', 'Country/Pays'])
    currency_col = _pick_col(df, ['Nom Devise', 'Devise', 'Currency', 'Monnaie'])

    lead_time_col = _pick_col(df, [
        'Lead_Time_Days',
        'Lead Time Days',
        'Lead Time',
        'LeadTime',
        'lead_time',
        'Delai Livraison',
        'Délai Livraison',
        'Délai',
        'Delai',
    ])
    lead_time_deviation_col = _pick_col(df, [
        'Lead_Time_Deviation_Days',
        'Lead Time Deviation Days',
        'LeadTime_Deviation',
        'Lead Time Deviation',
        'Lead_Time_Deviation',
    ])
    delivery_date_col = _pick_col(df, ['Date Liv.', 'Date Livraison', 'Date Livraison.', 'Date Expédition', 'Date Expedition', 'Date Réception', 'Date Reception'])
    late_flag_col = _pick_col(df, ['Late', 'En retard', 'Retard', 'is_late', 'Late Flag'])
    lead_time_target_col = _pick_col(df, ['Lead Time Target', 'SLA', 'Delai Cible', 'Délai Cible', 'Target Lead Time'])

    portfolio['meta'] = {
        'client_col': client_col,
        'date_col': date_col,
        'amount_col': amount_col,
        'order_col': order_col,
        'qty_col': qty_col,
        'pu_col': pu_col,
        'family_col': family_col,
        'product_col': product_col,
        'country_col': country_col,
        'currency_col': currency_col,
        'lead_time_col': lead_time_col,
        'lead_time_deviation_col': lead_time_deviation_col,
        'delivery_date_col': delivery_date_col,
        'late_flag_col': late_flag_col,
        'lead_time_target_col': lead_time_target_col,
        'time_granularity': tg,
        'period_label': period_label,
        'period_unit': period_unit,
        'period_adjective': period_adjective,
    }

    df_client = df.copy()
    df_client = df_client[df_client[client_col].astype(str) == str(client_id)].copy()
    if df_client.empty:
        portfolio['error'] = 'Client introuvable ou sans lignes'
        return portfolio

    if amount_col:
        df_client[amount_col] = pd.to_numeric(df_client[amount_col], errors='coerce')
    if date_col:
        df_client[date_col] = _to_datetime(df_client[date_col])
    if qty_col:
        df_client[qty_col] = pd.to_numeric(df_client[qty_col], errors='coerce')
    if pu_col:
        df_client[pu_col] = pd.to_numeric(df_client[pu_col], errors='coerce')

    # Définir une clé de commande (déduplication)
    if order_col and order_col in df_client.columns:
        order_key = df_client[order_col].astype(str)
        order_key = order_key.where(order_key.notna() & (order_key != 'nan') & (order_key != ''), other=df_client.index.astype(str))
    else:
        order_key = df_client.index.astype(str)

    df_client['_order_key'] = order_key

    # ===== KPIs de base =====
    ca_client = float(df_client[amount_col].sum()) if amount_col and amount_col in df_client.columns else None
    total_ca = None
    if amount_col and amount_col in df.columns:
        total_ca = pd.to_numeric(df[amount_col], errors='coerce').sum()
        total_ca = float(total_ca) if not pd.isna(total_ca) else None

    weight_pct = None
    if ca_client is not None and total_ca and total_ca != 0:
        weight_pct = float(ca_client / total_ca * 100)

    nb_lines = int(len(df_client))
    # nb_orders / ca_per_order sur commandes dédupliquées
    if amount_col and amount_col in df_client.columns:
        ca_by_order = df_client.groupby('_order_key')[amount_col].sum()
        nb_orders = int(ca_by_order.shape[0])
        ca_per_order = float(ca_by_order.mean()) if nb_orders else None
    else:
        nb_orders = int(df_client['_order_key'].nunique())
        ca_per_order = None

    panier_moyen_ligne = float(ca_client / nb_lines) if (ca_client is not None and nb_lines) else None

    # Dates order-level
    order_dates = None
    recency_days = None
    lifetime_days = None
    if date_col and date_col in df_client.columns:
        # date par commande = min date (robuste si lignes multiples)
        order_dates = df_client.groupby('_order_key')[date_col].min().dropna().sort_values()
        if not order_dates.empty:
            date_ref = pd.to_datetime(df[date_col], errors='coerce').max() if date_col in df.columns else order_dates.max()
            if pd.notna(date_ref):
                recency_days = int((date_ref - order_dates.max()).days)
            lifetime_days = int((order_dates.max() - order_dates.min()).days)

    # Fréquence
    orders_per_month = None
    orders_per_period = None
    median_interarrival = None
    p90_interarrival = None
    if order_dates is not None and len(order_dates) >= 1:
        # Compter les périodes actives selon la granularité demandée
        try:
            dmin = pd.to_datetime(order_dates.min(), errors='coerce')
            dmax = pd.to_datetime(order_dates.max(), errors='coerce')
            if pd.notna(dmin) and pd.notna(dmax):
                if tg == 'month':
                    first_p = dmin.to_period('M')
                    last_p = dmax.to_period('M')
                    active_periods = int((last_p - first_p).n) + 1 if hasattr((last_p - first_p), 'n') else 1
                elif tg == 'quarter':
                    first_p = dmin.to_period('Q-MAR')
                    last_p = dmax.to_period('Q-MAR')
                    active_periods = int((last_p - first_p).n) + 1 if hasattr((last_p - first_p), 'n') else 1
                else:
                    # Année fiscale (fin Mars)
                    first_p = dmin.to_period('A-MAR')
                    last_p = dmax.to_period('A-MAR')
                    active_periods = int((last_p - first_p).n) + 1 if hasattr((last_p - first_p), 'n') else 1
                active_periods = max(int(active_periods), 1)
                orders_per_period = float(nb_orders / active_periods) if nb_orders else None
                if tg == 'month':
                    orders_per_month = orders_per_period
        except Exception:
            orders_per_period = None

        if len(order_dates) >= 2:
            diffs = order_dates.diff().dropna().dt.days
            if not diffs.empty:
                median_interarrival = int(np.nanmedian(diffs.values))
                p90_interarrival = int(np.nanpercentile(diffs.values, 90))

    # ===== Lead time / late rate (sur commandes) =====
    lead_time_order = None
    if lead_time_col and lead_time_col in df_client.columns:
        df_client[lead_time_col] = pd.to_numeric(df_client[lead_time_col], errors='coerce')
        lead_time_order = df_client.groupby('_order_key')[lead_time_col].median()
    elif delivery_date_col and date_col and delivery_date_col in df_client.columns and date_col in df_client.columns:
        df_client[delivery_date_col] = _to_datetime(df_client[delivery_date_col])
        lt = (df_client[delivery_date_col] - df_client[date_col]).dt.days
        df_client['_lead_time_calc'] = pd.to_numeric(lt, errors='coerce')
        lead_time_order = df_client.groupby('_order_key')['_lead_time_calc'].median()

    lead_time_median = float(lead_time_order.median()) if isinstance(lead_time_order, pd.Series) and not lead_time_order.dropna().empty else None
    lead_time_p90 = float(np.nanpercentile(lead_time_order.dropna().values, 90)) if isinstance(lead_time_order, pd.Series) and lead_time_order.dropna().shape[0] >= 2 else None

    late_rate = None
    if late_flag_col and late_flag_col in df_client.columns:
        late_ser = df_client[late_flag_col]
        # normaliser vers 0/1
        if late_ser.dtype == bool:
            late_num = late_ser.astype(int)
        else:
            late_num = pd.to_numeric(late_ser, errors='coerce')
            if late_num.isna().all():
                late_num = late_ser.astype(str).str.lower().isin(['true', 'vrai', '1', 'yes', 'oui', 'late', 'retard']).astype(int)
        late_by_order = late_num.groupby(df_client['_order_key']).max()
        if late_by_order.notna().any():
            late_rate = float(late_by_order.mean())
    elif lead_time_deviation_col and lead_time_deviation_col in df_client.columns:
        dev = pd.to_numeric(df_client[lead_time_deviation_col], errors='coerce')
        if dev.notna().any():
            late_by_order = (dev > 0).astype(int).groupby(df_client['_order_key']).max()
            if late_by_order.notna().any():
                late_rate = float(late_by_order.mean())
    elif lead_time_order is not None and lead_time_target_col and lead_time_target_col in df_client.columns:
        target = pd.to_numeric(df_client[lead_time_target_col], errors='coerce')
        target_by_order = target.groupby(df_client['_order_key']).median()
        mask = lead_time_order.notna() & target_by_order.notna() & (target_by_order > 0)
        if mask.any():
            late_rate = float((lead_time_order[mask] > target_by_order[mask]).mean())

    # ===== Country / Currency =====
    country_mode = None
    if country_col and country_col in df_client.columns:
        vc = df_client[country_col].dropna().astype(str).value_counts()
        if not vc.empty:
            country_mode = str(vc.index[0])

    currency_mix = []
    if currency_col and currency_col in df_client.columns and amount_col and amount_col in df_client.columns:
        cur = df_client[[currency_col, amount_col]].dropna(subset=[currency_col]).copy()
        cur[currency_col] = cur[currency_col].astype(str)
        cur_sum = cur.groupby(currency_col)[amount_col].sum().sort_values(ascending=False)
        cur_total = float(cur_sum.sum()) if cur_sum.sum() else None
        for ccy, ca in cur_sum.head(10).items():
            currency_mix.append({
                'currency': str(ccy),
                'ca': float(ca),
                'share_pct': float(ca / cur_total * 100) if cur_total else None
            })

    # ===== Pricing (PU Net) =====
    pu_net_wmean = None
    pu_net_median = None
    pu_net_cv = None
    if pu_col and pu_col in df_client.columns:
        pu_vals = df_client[pu_col]
        pu_net_median = float(pu_vals.median()) if pu_vals.dropna().shape[0] else None
        if qty_col and qty_col in df_client.columns:
            pu_net_wmean = _weighted_mean(df_client[pu_col], df_client[qty_col])
        else:
            pu_net_wmean = float(pu_vals.mean()) if pu_vals.dropna().shape[0] else None
        if pu_net_wmean is not None and pu_net_wmean != 0 and pu_vals.dropna().shape[0] >= 2:
            pu_net_cv = float(pu_vals.std(ddof=1) / abs(pu_vals.mean())) if pu_vals.mean() not in [0, None, np.nan] else None

    # ===== Portfolio familles + concentration =====
    families_portfolio = []
    top_families = []
    top1_family_share = None
    hhi = None
    nb_families = None
    monthly_family_records = []
    if family_col and family_col in df_client.columns and amount_col and amount_col in df_client.columns:
        fam = df_client[[family_col, amount_col]].copy()
        fam[family_col] = fam[family_col].fillna('Non renseigné').astype(str)
        fam_sum = fam.groupby(family_col)[amount_col].sum().sort_values(ascending=False)
        nb_families = int(fam_sum.shape[0])

        ca_total_client = float(fam_sum.sum()) if fam_sum.sum() else None
        top_families = list(fam_sum.head(top_n_families).index)

        # Construire table top + Autres
        top_sum = fam_sum.head(top_n_families)
        other_ca = float(fam_sum.iloc[top_n_families:].sum()) if fam_sum.shape[0] > top_n_families else 0.0
        for fname, ca in top_sum.items():
            share = float(ca / ca_total_client * 100) if ca_total_client else None
            families_portfolio.append({'family': str(fname), 'ca': float(ca), 'share_pct': share})
        if other_ca > 0:
            families_portfolio.append({'family': 'Autres', 'ca': float(other_ca), 'share_pct': float(other_ca / ca_total_client * 100) if ca_total_client else None})

        if families_portfolio:
            top1_family_share = families_portfolio[0].get('share_pct')

        # HHI simple sur toutes les familles
        if ca_total_client and ca_total_client != 0:
            shares = (fam_sum / ca_total_client).values
            hhi = float(np.sum(np.square(shares)))

        # Mix familles dans le temps (granularité choisie)
        if date_col and date_col in df_client.columns:
            fam2 = df_client[[date_col, family_col, amount_col]].dropna(subset=[date_col]).copy()
            d = pd.to_datetime(fam2[date_col], errors='coerce')
            fam2 = fam2.assign(_d=d).dropna(subset=['_d'])
            if not fam2.empty:
                if tg == 'month':
                    fam2['_period_index'] = fam2['_d'].dt.year * 100 + fam2['_d'].dt.month
                    fam2['_period_label'] = fam2['_d'].dt.to_period('M').astype(str)
                elif tg == 'quarter':
                    fy = fam2['_d'].dt.year + (fam2['_d'].dt.month >= 4).astype(int)
                    qn = ((fam2['_d'].dt.month - 4) % 12) // 3 + 1
                    fam2['_period_index'] = fy * 10 + qn
                    if 'Fiscal_Quarter' in df_client.columns:
                        # Rejoindre via index (mêmes lignes) si la colonne existe
                        try:
                            fam2['_period_label'] = df_client.loc[fam2.index, 'Fiscal_Quarter'].astype(str)
                        except Exception:
                            fam2['_period_label'] = None
                    if '_period_label' not in fam2.columns or fam2['_period_label'].isna().all():
                        fam2['_period_label'] = ('Q' + qn.astype(int).astype(str) + ' FY' + fy.astype(int).astype(str))
                else:
                    fy = fam2['_d'].dt.year + (fam2['_d'].dt.month >= 4).astype(int)
                    fam2['_period_index'] = fy
                    if 'Fiscal_Year_Label' in df_client.columns:
                        try:
                            fam2['_period_label'] = df_client.loc[fam2.index, 'Fiscal_Year_Label'].astype(str)
                        except Exception:
                            fam2['_period_label'] = None
                    if '_period_label' not in fam2.columns or fam2['_period_label'].isna().all():
                        fam2['_period_label'] = ('FY' + fy.astype(int).astype(str))

                fam2[family_col] = fam2[family_col].fillna('Non renseigné').astype(str)
                fam2['family_bucket'] = np.where(fam2[family_col].isin(top_families), fam2[family_col], 'Autres')
                m = fam2.groupby(['_period_label', '_period_index', 'family_bucket'], dropna=False)[amount_col].sum().reset_index()
                m = m.sort_values(['_period_index', '_period_label'])
                for _, r in m.iterrows():
                    monthly_family_records.append({
                        'month': str(r['_period_label']),
                        'period': str(r['_period_label']),
                        'period_index': int(r['_period_index']) if not pd.isna(r['_period_index']) else None,
                        'family': str(r['family_bucket']),
                        'ca': float(r[amount_col]),
                    })

    portfolio['tables']['families_portfolio'] = families_portfolio

    # ===== Top produits =====
    top_products = []
    if product_col and product_col in df_client.columns and amount_col and amount_col in df_client.columns:
        prod = df_client[[product_col, amount_col]].copy()
        prod[product_col] = prod[product_col].fillna('Non renseigné').astype(str)
        prod_sum = prod.groupby(product_col)[amount_col].sum().sort_values(ascending=False)
        prod_total = float(prod_sum.sum()) if prod_sum.sum() else None
        for p, ca in prod_sum.head(top_n_products).items():
            top_products.append({
                'product': str(p),
                'ca': float(ca),
                'share_pct': float(ca / prod_total * 100) if prod_total else None
            })
    portfolio['tables']['top_products'] = top_products

    # ===== Lead time par produit (sur commandes) =====
    lead_time_by_product = []
    if product_col and product_col in df_client.columns and isinstance(lead_time_order, pd.Series) and not lead_time_order.empty:
        try:
            tmp = df_client[[product_col, '_order_key']].copy()
            tmp[product_col] = tmp[product_col].fillna('Non renseigné').astype(str)

            # Attacher lead time par commande à chaque ligne
            tmp = tmp.merge(
                lead_time_order.rename('lead_time').reset_index(),
                left_on='_order_key',
                right_on='_order_key',
                how='left',
            )

            # Late flag par commande si possible
            late_by_order = None
            if late_flag_col and late_flag_col in df_client.columns:
                late_ser = df_client[late_flag_col]
                if late_ser.dtype == bool:
                    late_num = late_ser.astype(int)
                else:
                    late_num = pd.to_numeric(late_ser, errors='coerce')
                    if late_num.isna().all():
                        late_num = late_ser.astype(str).str.lower().isin(['true', 'vrai', '1', 'yes', 'oui', 'late', 'retard']).astype(int)
                late_by_order = late_num.groupby(df_client['_order_key']).max()
            elif lead_time_deviation_col and lead_time_deviation_col in df_client.columns:
                dev = pd.to_numeric(df_client[lead_time_deviation_col], errors='coerce')
                late_by_order = (dev > 0).astype(int).groupby(df_client['_order_key']).max()
            if isinstance(late_by_order, pd.Series):
                tmp = tmp.merge(
                    late_by_order.rename('late_flag').reset_index(),
                    left_on='_order_key',
                    right_on='_order_key',
                    how='left',
                )

            # CA produit (optionnel)
            if amount_col and amount_col in df_client.columns:
                ca_prod = (
                    df_client[[product_col, amount_col]]
                    .copy()
                    .assign(**{product_col: lambda x: x[product_col].fillna('Non renseigné').astype(str)})
                    .groupby(product_col)[amount_col]
                    .sum()
                )
            else:
                ca_prod = None

            g = tmp.dropna(subset=['lead_time']).groupby(product_col)
            rows = []
            for prod_name, grp in g:
                lt = pd.to_numeric(grp['lead_time'], errors='coerce').dropna()
                if lt.empty:
                    continue
                nb_orders_prod = int(grp['_order_key'].nunique())
                med = float(np.nanmedian(lt.values))
                p90 = float(np.nanpercentile(lt.values, 90)) if lt.shape[0] >= 2 else None
                late_rate_prod = None
                if 'late_flag' in grp.columns and pd.to_numeric(grp['late_flag'], errors='coerce').notna().any():
                    # Late_flag est répété par ligne; on repasse par commande pour éviter les doublons
                    tmp_orders = grp.dropna(subset=['late_flag']).groupby('_order_key')['late_flag'].max()
                    if not tmp_orders.empty:
                        late_rate_prod = float(pd.to_numeric(tmp_orders, errors='coerce').mean())

                ca_val = float(ca_prod.get(prod_name)) if isinstance(ca_prod, pd.Series) and prod_name in ca_prod.index else None
                rows.append({
                    'product': str(prod_name),
                    'nb_orders': nb_orders_prod,
                    'lead_time_median': med,
                    'lead_time_p90': p90,
                    'late_rate_pct': float(late_rate_prod * 100) if late_rate_prod is not None else None,
                    'ca': ca_val,
                })

            # Trier: par CA si dispo sinon par nb commandes
            if rows:
                if any(r.get('ca') is not None for r in rows):
                    rows = sorted(rows, key=lambda r: (r.get('ca') is None, -(r.get('ca') or 0.0)))
                else:
                    rows = sorted(rows, key=lambda r: -(r.get('nb_orders') or 0))

                lead_time_by_product = rows[:top_n_products]
        except Exception as e:
            print(f"[client360] lead_time_by_product error: {e}")

    portfolio['tables']['lead_time_by_product'] = lead_time_by_product

    # ===== Monthly summary =====
    monthly_summary = []
    monthly_orders_records = []
    monthly_lead_records = []
    monthly_pu_family_records = []
    if date_col and date_col in df_client.columns:
        df_m = df_client.dropna(subset=[date_col]).copy()

        # Période (label + index de tri)
        d = pd.to_datetime(df_m[date_col], errors='coerce')
        df_m = df_m.assign(_d=d).dropna(subset=['_d'])
        if not df_m.empty:
            if tg == 'month':
                df_m['_period_index'] = df_m['_d'].dt.year * 100 + df_m['_d'].dt.month
                df_m['_period_label'] = df_m['_d'].dt.to_period('M').astype(str)
            elif tg == 'quarter':
                fy = df_m['_d'].dt.year + (df_m['_d'].dt.month >= 4).astype(int)
                qn = ((df_m['_d'].dt.month - 4) % 12) // 3 + 1
                df_m['_period_index'] = fy * 10 + qn
                if 'Fiscal_Quarter' in df_m.columns and df_m['Fiscal_Quarter'].notna().any():
                    df_m['_period_label'] = df_m['Fiscal_Quarter'].astype(str)
                else:
                    df_m['_period_label'] = ('Q' + qn.astype(int).astype(str) + ' FY' + fy.astype(int).astype(str))
            else:
                fy = df_m['_d'].dt.year + (df_m['_d'].dt.month >= 4).astype(int)
                df_m['_period_index'] = fy
                if 'Fiscal_Year_Label' in df_m.columns and df_m['Fiscal_Year_Label'].notna().any():
                    df_m['_period_label'] = df_m['Fiscal_Year_Label'].astype(str)
                else:
                    df_m['_period_label'] = ('FY' + fy.astype(int).astype(str))

        # Garder compat: beaucoup de code/visus attendent la clé 'month'
        df_m['month'] = df_m.get('_period_label')
        df_m['period'] = df_m.get('_period_label')

        # order-level aggregates for lead time
        order_level = df_m.groupby(['month', '_order_key']).agg({
            amount_col: 'sum' if amount_col else 'size',
            pu_col: 'median' if pu_col else 'size',
        })

        # Lead time order-level by month
        if isinstance(lead_time_order, pd.Series) and not lead_time_order.empty:
            lt_order = lead_time_order.rename('lead_time').to_frame()
            # attach month per order
            order_month = df_m.groupby('_order_key')['month'].first()
            lt_order = lt_order.join(order_month, how='left')
            lt_by_month = lt_order.dropna(subset=['month']).groupby('month')['lead_time']
        else:
            lt_by_month = None

        # pricing weighted per month
        if pu_col and pu_col in df_m.columns and qty_col and qty_col in df_m.columns:
            pu_w = (
                df_m.dropna(subset=[pu_col, qty_col])
                .assign(_px=lambda x: x[pu_col] * x[qty_col])
                .groupby('month')
                .agg(px_sum=('_px', 'sum'), qty_sum=(qty_col, 'sum'))
            )
            pu_w['pu_weighted'] = pu_w['px_sum'] / pu_w['qty_sum'].replace({0: np.nan})
            pu_weighted_by_month = pu_w['pu_weighted'].to_dict()
        elif pu_col and pu_col in df_m.columns:
            pu_weighted_by_month = df_m.groupby('month')[pu_col].mean().to_dict()
        else:
            pu_weighted_by_month = {}

        # CA and orders per month
        if amount_col and amount_col in df_m.columns:
            ca_by_month = df_m.groupby('month')[amount_col].sum().to_dict()
        else:
            ca_by_month = df_m.groupby('month').size().to_dict()

        orders_by_month = df_m.groupby('month')['_order_key'].nunique().to_dict()

        # Tri fiable (strings de trimestre/année ne se trient pas bien)
        periods_sorted = (
            df_m[['month', '_period_index']]
            .dropna(subset=['month'])
            .drop_duplicates()
            .sort_values(['_period_index', 'month'])
        )
        months_sorted = periods_sorted['month'].astype(str).tolist()
        period_index_map = {str(r['month']): int(r['_period_index']) for _, r in periods_sorted.iterrows() if not pd.isna(r.get('_period_index'))}

        for m in months_sorted:
            ca_m = float(ca_by_month.get(m, 0.0))
            nb_o = int(orders_by_month.get(m, 0))
            pu_m = _safe_float(pu_weighted_by_month.get(m))

            lt_med = None
            lt_p90 = None
            if lt_by_month is not None and m in lt_by_month.groups:
                vals = lt_by_month.get_group(m).dropna().values
                if vals.size:
                    lt_med = float(np.nanmedian(vals))
                if vals.size >= 2:
                    lt_p90 = float(np.nanpercentile(vals, 90))

            monthly_summary.append({
                'month': str(m),
                'period': str(m),
                'period_index': int(period_index_map.get(str(m))) if str(m) in period_index_map else None,
                'ca': ca_m,
                'nb_orders': nb_o,
                'pu_net_weighted': pu_m,
                'lead_time_median': lt_med,
                'lead_time_p90': lt_p90,
            })
            monthly_orders_records.append({'month': str(m), 'period': str(m), 'period_index': int(period_index_map.get(str(m))) if str(m) in period_index_map else None, 'ca': ca_m, 'nb_orders': nb_o})
            monthly_lead_records.append({'month': str(m), 'period': str(m), 'period_index': int(period_index_map.get(str(m))) if str(m) in period_index_map else None, 'lead_time_median': lt_med, 'lead_time_p90': lt_p90})

        # PU Net par famille (toutes les familles achetées) dans le temps
        if family_col and family_col in df_m.columns and pu_col and pu_col in df_m.columns:
            try:
                df_f = df_m[['month', family_col, pu_col] + ([qty_col] if qty_col and qty_col in df_m.columns else []) + ([amount_col] if amount_col and amount_col in df_m.columns else [])].copy()
                df_f[family_col] = df_f[family_col].fillna('Non renseigné').astype(str)
                df_f[pu_col] = pd.to_numeric(df_f[pu_col], errors='coerce')
                if qty_col and qty_col in df_f.columns:
                    df_f[qty_col] = pd.to_numeric(df_f[qty_col], errors='coerce')
                if amount_col and amount_col in df_f.columns:
                    df_f[amount_col] = pd.to_numeric(df_f[amount_col], errors='coerce')

                if qty_col and qty_col in df_f.columns:
                    df_f = df_f.dropna(subset=[pu_col, qty_col])
                    df_f = df_f[df_f[qty_col] > 0]
                    if not df_f.empty:
                        df_f['_px'] = df_f[pu_col] * df_f[qty_col]
                        g = df_f.groupby(['month', family_col], dropna=False).agg(
                            px_sum=('_px', 'sum'),
                            qty_sum=(qty_col, 'sum'),
                            ca_sum=(amount_col, 'sum') if (amount_col and amount_col in df_f.columns) else ('_px', 'size'),
                        )
                        g['pu_net_weighted'] = g['px_sum'] / g['qty_sum'].replace({0: np.nan})
                        g = g.reset_index()
                        for _, r in g.iterrows():
                            pu_val = _safe_float(r.get('pu_net_weighted'))
                            if pu_val is None:
                                continue
                            monthly_pu_family_records.append({
                                'month': str(r['month']),
                                'period': str(r['month']),
                                'period_index': int(period_index_map.get(str(r['month']))) if str(r['month']) in period_index_map else None,
                                'family': str(r[family_col]),
                                'pu_net_weighted': pu_val,
                                'ca': _safe_float(r.get('ca_sum')),
                            })
                else:
                    df_f = df_f.dropna(subset=[pu_col])
                    if not df_f.empty:
                        g = df_f.groupby(['month', family_col], dropna=False).agg(
                            pu_net_weighted=(pu_col, 'mean'),
                            ca_sum=(amount_col, 'sum') if (amount_col and amount_col in df_f.columns) else (pu_col, 'size'),
                        ).reset_index()
                        for _, r in g.iterrows():
                            pu_val = _safe_float(r.get('pu_net_weighted'))
                            if pu_val is None:
                                continue
                            monthly_pu_family_records.append({
                                'month': str(r['month']),
                                'period': str(r['month']),
                                'period_index': int(period_index_map.get(str(r['month']))) if str(r['month']) in period_index_map else None,
                                'family': str(r[family_col]),
                                'pu_net_weighted': pu_val,
                                'ca': _safe_float(r.get('ca_sum')),
                            })
            except Exception as e:
                print(f"[client360] pu_over_time_by_family error: {e}")

    portfolio['tables']['monthly_summary'] = monthly_summary

    # ===== Impact lead time -> commandes/CA (mensuel + inter-arrival) =====
    lt_orders_corr_same = None
    lt_ca_corr_same = None
    lt_orders_corr_lag1 = None
    lt_ca_corr_lag1 = None

    gap_median_after_high_lt = None
    gap_median_after_low_lt = None
    gap_delta_days = None
    high_lt_threshold = None
    nb_orders_high_lt = None
    nb_orders_low_lt = None
    gap_records = []

    # Corrélations mensuelles (LT du mois t vs commandes/CA du mois t et t+1)
    try:
        if monthly_summary and any(r.get('lead_time_median') is not None for r in monthly_summary):
            mdf = pd.DataFrame(monthly_summary).copy()
            if not mdf.empty and {'month', 'nb_orders', 'ca'}.issubset(mdf.columns):
                if 'period_index' in mdf.columns and pd.to_numeric(mdf['period_index'], errors='coerce').notna().any():
                    mdf['period_index'] = pd.to_numeric(mdf['period_index'], errors='coerce')
                    mdf = mdf.sort_values('period_index')
                else:
                    mdf = mdf.sort_values('month')
                # Choisir une série LT (médiane prioritaire, sinon P90)
                if 'lead_time_median' in mdf.columns and pd.to_numeric(mdf['lead_time_median'], errors='coerce').notna().any():
                    mdf['lt'] = pd.to_numeric(mdf['lead_time_median'], errors='coerce')
                else:
                    mdf['lt'] = pd.to_numeric(mdf.get('lead_time_p90'), errors='coerce')
                mdf['orders'] = pd.to_numeric(mdf['nb_orders'], errors='coerce')
                mdf['ca_num'] = pd.to_numeric(mdf['ca'], errors='coerce')

                # same-month corr
                tmp_same = mdf[['lt', 'orders', 'ca_num']].dropna()
                if tmp_same.shape[0] >= 3 and tmp_same['lt'].nunique() >= 2:
                    lt_orders_corr_same = float(tmp_same['lt'].corr(tmp_same['orders'])) if tmp_same['orders'].nunique() >= 2 else None
                    lt_ca_corr_same = float(tmp_same['lt'].corr(tmp_same['ca_num'])) if tmp_same['ca_num'].nunique() >= 2 else None

                # lag-1 corr: lt_t vs orders_{t+1}
                mdf['orders_next'] = mdf['orders'].shift(-1)
                mdf['ca_next'] = mdf['ca_num'].shift(-1)
                tmp_lag = mdf[['lt', 'orders_next', 'ca_next']].dropna()
                if tmp_lag.shape[0] >= 3 and tmp_lag['lt'].nunique() >= 2:
                    lt_orders_corr_lag1 = float(tmp_lag['lt'].corr(tmp_lag['orders_next'])) if tmp_lag['orders_next'].nunique() >= 2 else None
                    lt_ca_corr_lag1 = float(tmp_lag['lt'].corr(tmp_lag['ca_next'])) if tmp_lag['ca_next'].nunique() >= 2 else None
    except Exception as e:
        print(f"[client360] lead_time impact corr error: {e}")

    # Inter-arrival après un lead time élevé (sur commandes dédupliquées)
    try:
        if isinstance(order_dates, pd.Series) and isinstance(lead_time_order, pd.Series):
            od = order_dates.dropna()
            lt = lead_time_order.dropna()
            common_idx = od.index.intersection(lt.index)
            if common_idx.shape[0] >= 4:
                o = pd.DataFrame({
                    'order_date': pd.to_datetime(od.loc[common_idx], errors='coerce'),
                    'lead_time': pd.to_numeric(lt.loc[common_idx], errors='coerce'),
                }).dropna().sort_values('order_date')

                if o.shape[0] >= 4 and o['lead_time'].notna().any():
                    o['gap_next_days'] = (o['order_date'].shift(-1) - o['order_date']).dt.days
                    o = o.dropna(subset=['gap_next_days'])
                    if o.shape[0] >= 3 and o['lead_time'].nunique() >= 2:
                        high_lt_threshold = float(np.nanpercentile(o['lead_time'].values, 75))
                        high_mask = o['lead_time'] >= high_lt_threshold
                        low_mask = ~high_mask
                        nb_orders_high_lt = int(high_mask.sum())
                        nb_orders_low_lt = int(low_mask.sum())
                        if nb_orders_high_lt >= 2:
                            gap_median_after_high_lt = float(np.nanmedian(o.loc[high_mask, 'gap_next_days'].values))
                        if nb_orders_low_lt >= 2:
                            gap_median_after_low_lt = float(np.nanmedian(o.loc[low_mask, 'gap_next_days'].values))
                        if gap_median_after_high_lt is not None and gap_median_after_low_lt is not None:
                            gap_delta_days = float(gap_median_after_high_lt - gap_median_after_low_lt)

                        # Records pour boxplot (limiter la taille)
                        if o.shape[0] > 0:
                            max_points = 600
                            oh = o.loc[high_mask, 'gap_next_days'].dropna().astype(float).head(max_points)
                            ol = o.loc[low_mask, 'gap_next_days'].dropna().astype(float).head(max_points)
                            gap_records = (
                                [{'group': 'LT ≥ P75', 'gap_next_days': float(v)} for v in oh.values]
                                + [{'group': 'LT < P75', 'gap_next_days': float(v)} for v in ol.values]
                            )
    except Exception as e:
        print(f"[client360] lead_time impact interarrival error: {e}")

    # ===== Alerts simples =====
    alerts = []
    if top1_family_share is not None and top1_family_share >= 70:
        alerts.append({'type': 'warning', 'text': f"Forte concentration: la 1ère famille pèse {top1_family_share:.1f}% du CA."})
    if recency_days is not None and recency_days >= 90:
        alerts.append({'type': 'warning', 'text': f"Client dormant: dernière commande il y a {recency_days} jours."})
    if pu_net_cv is not None and pu_net_cv >= 0.30:
        alerts.append({'type': 'warning', 'text': f"Pricing instable: CV PU Net = {pu_net_cv:.2f}."})
    if lead_time_p90 is not None and lead_time_p90 >= 30:
        alerts.append({'type': 'warning', 'text': f"Lead time élevé: P90 = {lead_time_p90:.1f} jours."})
    if late_rate is not None and late_rate >= 0.20:
        alerts.append({'type': 'warning', 'text': f"Taux de retard élevé: {late_rate*100:.1f}% des commandes."})

    # Baisse récente (3 derniers mois vs 3 mois précédents)
    if len(monthly_orders_records) >= 6:
        mdf = pd.DataFrame(monthly_orders_records).copy()
        if 'period_index' in mdf.columns and pd.to_numeric(mdf['period_index'], errors='coerce').notna().any():
            mdf = mdf.sort_values('period_index')
        else:
            mdf = mdf.sort_values('month')
        last3 = mdf.tail(3)['ca'].sum()
        prev3 = mdf.tail(6).head(3)['ca'].sum()
        if prev3 > 0 and (last3 / prev3) <= 0.70:
            alerts.append({'type': 'warning', 'text': f"Baisse récente du CA (3 derniers {period_unit}s vs 3 précédents)."})

    portfolio['alerts'] = alerts

    # ===== KPIs pack =====
    portfolio['kpis'] = {
        'ca_client': _safe_float(ca_client),
        'weight_pct': _safe_float(weight_pct),
        'nb_orders': _safe_int(nb_orders),
        'ca_per_order': _safe_float(ca_per_order),
        'panier_moyen_ligne': _safe_float(panier_moyen_ligne),
        'recency_days': _safe_int(recency_days),
        'lifetime_days': _safe_int(lifetime_days),
        'orders_per_month': _safe_float(orders_per_month),
        'orders_per_period': _safe_float(orders_per_period),
        'median_interarrival_days': _safe_int(median_interarrival),
        'p90_interarrival_days': _safe_int(p90_interarrival),
        'lead_time_median': _safe_float(lead_time_median),
        'lead_time_p90': _safe_float(lead_time_p90),
        'late_rate': _safe_float(late_rate),
        'late_rate_pct': _safe_float(late_rate * 100) if late_rate is not None else None,
        'lt_orders_corr_same': _safe_float(lt_orders_corr_same),
        'lt_ca_corr_same': _safe_float(lt_ca_corr_same),
        'lt_orders_corr_lag1': _safe_float(lt_orders_corr_lag1),
        'lt_ca_corr_lag1': _safe_float(lt_ca_corr_lag1),
        'lt_high_threshold_p75': _safe_float(high_lt_threshold),
        'gap_median_after_high_lt': _safe_float(gap_median_after_high_lt),
        'gap_median_after_low_lt': _safe_float(gap_median_after_low_lt),
        'gap_delta_days': _safe_float(gap_delta_days),
        'nb_orders_high_lt': _safe_int(nb_orders_high_lt),
        'nb_orders_low_lt': _safe_int(nb_orders_low_lt),
        'country': country_mode,
        'currency_mix': currency_mix,
        'pu_net_weighted_mean': _safe_float(pu_net_wmean),
        'pu_net_median': _safe_float(pu_net_median),
        'pu_net_cv': _safe_float(pu_net_cv),
        'nb_families': _safe_int(nb_families),
        'top1_family_share_pct': _safe_float(top1_family_share),
        'hhi': _safe_float(hhi),
    }

    # ===== Graphes (Plotly HTML) =====
    try:
        from .visualizations import viz_clients

        # Pie familles
        portfolio['graphs']['families_pie'] = viz_clients.create_client_mix_families_pie(families_portfolio)
        # Stacked familles dans le temps
        portfolio['graphs']['families_stacked'] = viz_clients.create_client_mix_families_stacked(monthly_family_records, period_label=period_label)
        # Orders over time
        portfolio['graphs']['orders_over_time'] = viz_clients.create_client_orders_over_time(monthly_orders_records, period_label=period_label, period_adjective=period_adjective)

        # PU Net par mois (client + toutes les familles sur le même graphique)
        portfolio['graphs']['pu_over_time'] = viz_clients.create_client_pu_over_time(
            monthly_summary,
            monthly_product_pu_records=monthly_pu_family_records,
            top_n_products=None,
            period_label=period_label,
            period_adjective=period_adjective,
        )

        # Lead time figs (préparer df minimal)
        if lead_time_order is not None:
            # on repart de df_client avec une colonne lead_time si possible
            if lead_time_col and lead_time_col in df_client.columns:
                df_lt = df_client[[lead_time_col]].rename(columns={lead_time_col: 'lead_time'})
            elif '_lead_time_calc' in df_client.columns:
                df_lt = df_client[['_lead_time_calc']].rename(columns={'_lead_time_calc': 'lead_time'})
            else:
                df_lt = None
            if df_lt is not None:
                portfolio['graphs']['lead_time_hist'] = viz_clients.create_client_lead_time_hist(df_lt)
            portfolio['graphs']['lead_time_over_time'] = viz_clients.create_client_lead_time_over_time(monthly_lead_records, period_label=period_label)

        # Impact lead time -> activité
        portfolio['graphs']['lead_time_impact'] = viz_clients.create_client_lead_time_impact_chart(
            monthly_summary,
            gap_records=gap_records,
            high_lt_threshold=high_lt_threshold,
            period_label=period_label,
        )
    except Exception as e:
        print(f"[client360] Graph generation error: {e}")

    return portfolio


def analyze_clients(df_final: pd.DataFrame, time_granularity: str | None = None) -> dict:
    """
    Analyse détaillée des clients : segmentation, RFM, concentration
    
    Args:
        df_final: DataFrame nettoyé
    
    Returns:
        dict avec l'analyse des clients
    """
    
    def _to_datetime(s: pd.Series):
        try:
            return pd.to_datetime(s, errors='coerce', dayfirst=True, infer_datetime_format=True)
        except Exception:
            return pd.to_datetime(s, errors='coerce')

    tg = str(time_granularity or '').lower().strip() if time_granularity is not None else None
    if tg in ['fiscal', 'fiscal_year', 'fiscale', 'annuel', 'annuelle']:
        tg = 'year'
    if tg not in [None, 'month', 'quarter', 'year']:
        tg = None

    period_label = 'Commande'
    period_unit = 'commande'
    period_adjective = 'par commande'
    if tg == 'month':
        period_label = 'Mois'
        period_unit = 'mois'
        period_adjective = 'mensuel'
    elif tg == 'quarter':
        period_label = 'Trimestre'
        period_unit = 'trimestre'
        period_adjective = 'trimestriel'
    elif tg == 'year':
        period_label = 'Année fiscale'
        period_unit = 'année'
        period_adjective = 'annuel'

    results = {
        'meta': {
            'time_granularity': tg or 'raw',
            'period_label': period_label,
            'period_unit': period_unit,
            'period_adjective': period_adjective,
        }
    }
    
    # 1. STATISTIQUES DE BASE PAR CLIENT

    if 'Cpt Client' in df_final.columns and 'Montant' in df_final.columns:
        df2 = df_final.copy()
        df2['Montant'] = pd.to_numeric(df2['Montant'], errors='coerce')

        if tg in ['month', 'quarter', 'year'] and 'Date Fact.' in df2.columns:
            df2['Date Fact.'] = _to_datetime(df2['Date Fact.'])
            dt = df2['Date Fact.']

            if tg == 'month':
                # YYYY-MM
                df2['_period'] = dt.dt.to_period('M').astype(str)
            elif tg == 'quarter':
                # Trimestre fiscal (Avr-Mar) : FY = year + (month>=4)
                month = dt.dt.month
                year = dt.dt.year
                fy = year + (month >= 4).astype(int)
                q = (((month - 4) % 12) // 3 + 1).astype(int)
                df2['_period'] = 'Q' + q.astype(str) + ' FY' + fy.astype(str)
            else:
                # Année fiscale
                month = dt.dt.month
                year = dt.dt.year
                fy = year + (month >= 4).astype(int)
                df2['_period'] = 'FY' + fy.astype(str)

            # Si dispo, préférer les libellés déjà présents dans le dataset traité
            if tg == 'quarter' and 'Fiscal_Quarter' in df2.columns:
                df2['_period'] = df2['Fiscal_Quarter'].astype(str).where(df2['Fiscal_Quarter'].notna(), df2['_period'])
            if tg == 'year' and 'Fiscal_Year_Label' in df2.columns:
                df2['_period'] = df2['Fiscal_Year_Label'].astype(str).where(df2['Fiscal_Year_Label'].notna(), df2['_period'])

            per = df2.groupby(['Cpt Client', '_period'], dropna=False).agg({
                'Montant': ['sum', 'count'],
                'Date Fact.': ['min', 'max']
            })

            # Colonnes multi-index -> flat
            per.columns = ['CA_Period', 'Nb_Lignes_Period', 'Date_Premiere_Period', 'Date_Derniere_Period']
            per = per.reset_index()

            # Stats client (Fréquence = nb de périodes actives)
            client_stats = per.groupby('Cpt Client', dropna=False).agg({
                'CA_Period': ['sum', 'mean'],
                'Nb_Lignes_Period': 'sum',
                '_period': 'nunique',
                'Date_Premiere_Period': 'min',
                'Date_Derniere_Period': 'max'
            })

            client_stats.columns = ['CA_Total', 'Panier_Moyen', 'Nb_Lignes', 'Nb_Commandes', 'Date_Premiere', 'Date_Derniere']
            client_stats['CA_par_Commande'] = client_stats['CA_Total'] / client_stats['Nb_Commandes']

            if 'Date_Derniere' in client_stats.columns:
                date_ref = df2['Date Fact.'].max()
                if pd.notna(date_ref):
                    client_stats['Recence_Jours'] = (date_ref - client_stats['Date_Derniere']).dt.days

            client_stats = client_stats.sort_values('CA_Total', ascending=False)
            results['client_stats'] = client_stats
        else:
            # Mode historique (sans granularité) : Fréquence = nb de commandes (N° Bon)
            client_stats = df2.groupby('Cpt Client').agg({
                'Montant': ['sum', 'count', 'mean'],
                'N° Bon': 'nunique' if 'N° Bon' in df2.columns else 'count',
                'Date Fact.': ['min', 'max'] if 'Date Fact.' in df2.columns else 'count'
            })

            client_stats.columns = ['CA_Total', 'Nb_Lignes', 'Panier_Moyen',
                                    'Nb_Commandes', 'Date_Premiere', 'Date_Derniere']

            client_stats['CA_par_Commande'] = client_stats['CA_Total'] / client_stats['Nb_Commandes']

            if 'Date_Derniere' in client_stats.columns and 'Date Fact.' in df2.columns:
                date_ref = _to_datetime(df2['Date Fact.']).max()
                if pd.notna(date_ref):
                    # S'assurer que Date_Derniere est bien datetime
                    try:
                        client_stats['Date_Derniere'] = _to_datetime(client_stats['Date_Derniere'])
                    except Exception:
                        pass
                    client_stats['Recence_Jours'] = (date_ref - client_stats['Date_Derniere']).dt.days

            client_stats = client_stats.sort_values('CA_Total', ascending=False)
            results['client_stats'] = client_stats
    
    # 2. CONCENTRATION CLIENT (PARETO)
    
    if 'client_stats' in results:
        client_stats['Part_CA_Pct'] = (client_stats['CA_Total'] / client_stats['CA_Total'].sum() * 100)
        client_stats['Part_CA_Cumul'] = client_stats['Part_CA_Pct'].cumsum()
        
        # Top 20% clients
        top20_threshold = len(client_stats) * 0.2
        top20_clients = client_stats.head(int(top20_threshold))
        
        # Top 10 clients
        top10 = client_stats.head(10)
        
        results['top20_clients'] = top20_clients
        results['top10_clients'] = top10
        results['concentration_top20_pct'] = top20_clients['Part_CA_Pct'].sum()
        results['concentration_top10_pct'] = top10['Part_CA_Pct'].sum()
    
    # 3. SEGMENTATION RFM (Récence, Fréquence, Montant)
    
    if 'client_stats' in results and 'Recence_Jours' in client_stats.columns:
        def _qcut_score(series: pd.Series, q: int = 5, higher_is_better: bool = True) -> pd.Series:
            """Retourne un score 1..q robuste (évite les erreurs qcut sur valeurs dupliquées)."""
            s = pd.to_numeric(series, errors='coerce')
            n = int(s.notna().sum())
            if n < 2:
                return pd.Series([3] * len(s), index=s.index)
            q_eff = int(min(q, n))

            # Rank unique => plus de bins supprimés par duplicates='drop'
            r = s.rank(method='first', ascending=True)
            labels = list(range(1, q_eff + 1))
            try:
                b = pd.qcut(r, q=q_eff, labels=labels)
            except Exception:
                # fallback très défensif
                return pd.Series([3] * len(s), index=s.index)

            scores = pd.to_numeric(b, errors='coerce')
            if higher_is_better:
                return scores
            # lower is better (récence) => inversion
            return (q_eff + 1 - scores)

        # Calcul des scores RFM (1-5, 5 = meilleur)
        client_stats['R_Score'] = _qcut_score(client_stats['Recence_Jours'], q=5, higher_is_better=False)
        client_stats['F_Score'] = _qcut_score(client_stats['Nb_Commandes'], q=5, higher_is_better=True)
        client_stats['M_Score'] = _qcut_score(client_stats['CA_Total'], q=5, higher_is_better=True)
        
        # Score RFM global
        client_stats['RFM_Score'] = (
            client_stats['R_Score'].astype(int) +
            client_stats['F_Score'].astype(int) +
            client_stats['M_Score'].astype(int)
        )
        
        # Segmentation
        def classify_rfm(score):
            if score >= 13:
                return 'Champions'
            elif score >= 10:
                return 'Fidèles'
            elif score >= 7:
                return 'Potentiels'
            else:
                return 'Risque'

        # Compatibilité : certaines visualisations attendent la colonne 'RFM_Segment'.
        client_stats['RFM_Segment'] = client_stats['RFM_Score'].apply(classify_rfm)
        client_stats['Segment_RFM'] = client_stats['RFM_Segment']
        
        # Résumé par segment
        rfm_summary = client_stats.groupby('Segment_RFM').agg({
            'CA_Total': ['sum', 'count'],
            'Nb_Commandes': 'mean',
            'Recence_Jours': 'mean'
        })
        rfm_summary.columns = ['CA_Total', 'Nb_Clients', 'Freq_Moyenne', 'Recence_Moyenne']
        
        results['rfm_summary'] = rfm_summary
        results['client_stats'] = client_stats  # Mise à jour avec scores RFM
    
    # 4. ANALYSE PAR PAYS
    
    if 'Country' in df_final.columns:
        country_client_stats = df_final.groupby('Country').agg({
            'Cpt Client': 'nunique',
            'Montant': 'sum'
        }).sort_values('Montant', ascending=False)
        
        country_client_stats.columns = ['Nb_Clients', 'CA_Total']
        country_client_stats['CA_par_Client'] = country_client_stats['CA_Total'] / country_client_stats['Nb_Clients']
        
        results['country_client_stats'] = country_client_stats
    
    # 5. GÉNÉRATION DES VISUALISATIONS
    
    client_graphs = {}
    
    if 'client_stats' in results:
        from .visualizations import viz_clients
        
        # Graphique de concentration (Pareto)
        concentration_chart = viz_clients.create_client_concentration_chart(results['client_stats'])
        if concentration_chart:
            client_graphs['concentration'] = concentration_chart
        
        # Distribution RFM
        if 'RFM_Segment' in results['client_stats'].columns:
            rfm_chart = viz_clients.create_rfm_distribution_chart(results['client_stats'])
            if rfm_chart:
                client_graphs['rfm_distribution'] = rfm_chart
        
        # Distribution du CA
        ca_dist_chart = viz_clients.create_client_ca_distribution_chart(results['client_stats'])
        if ca_dist_chart:
            client_graphs['ca_distribution'] = ca_dist_chart
    
    results['client_graphs'] = client_graphs

    # KPIs dédiés au bloc clients (pour éviter de dépendre des KPIs globaux)
    if 'client_stats' in results and results['client_stats'] is not None and not results['client_stats'].empty:
        cs = results['client_stats']
        results['kpis'] = {
            'nb_clients': int(cs.shape[0]),
            # CA moyen total par client
            'ca_moyen_client': float(cs['CA_Total'].mean()) if 'CA_Total' in cs.columns else None,
            # CA moyen "par fréquence" (commande ou période active selon granularité)
            'ca_moyen_par_unite_freq': float(cs['CA_par_Commande'].mean()) if 'CA_par_Commande' in cs.columns else None,
        }
    else:
        results['kpis'] = {'nb_clients': None, 'ca_moyen_client': None, 'ca_moyen_par_unite_freq': None}
    
    return results


def generate_client_analysis(df_final: pd.DataFrame) -> dict:
    """
    Wrapper pour l'analyse clients - utilisé dans les views
    
    Args:
        df_final: DataFrame nettoyé
    
    Returns:
        dict avec l'analyse complète des clients
    """
    return analyze_clients(df_final)
