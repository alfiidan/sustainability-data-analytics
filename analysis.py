"""Task 3: reproducible GDP–GHG integration and statistical analysis.
Run from the repository root: python task3/analysis.py --source raw
Or use the historical cleaned panel: python task3/analysis.py --source snapshot
"""
from pathlib import Path
import argparse
import hashlib
import json
import urllib.request

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent if HERE.name == "task3" else HERE
YEARS = list(range(1990, 2021))
SNAPSHOT = ('https://raw.githubusercontent.com/alfiidan/'
            'sustainability-data-analytics/9af7a803b1aa2836e9076adbc310cfe2dde9739f/'
            'clean_ghg_gdp.csv')
SNAPSHOT_BLOB_SHA = '0ef07ab67349973eb427fbba49e9e99d4ac9432c'

# UNSD numeric country ID -> ISO 3166-1 alpha-3 code, observed country name,
# and geographical subregion (UN M49-style grouping). The sample is fixed to the 43 matched countries.
COUNTRIES = {
    36: ('AUS', 'Australia', 'Oceania'),
    40: ('AUT', 'Austria', 'Western Europe'),
    112: ('BLR', 'Belarus', 'Eastern Europe'),
    56: ('BEL', 'Belgium', 'Western Europe'),
    100: ('BGR', 'Bulgaria', 'Eastern Europe'),
    124: ('CAN', 'Canada', 'Northern America'),
    191: ('HRV', 'Croatia', 'Southern Europe'),
    196: ('CYP', 'Cyprus', 'Western Asia'),
    203: ('CZE', 'Czechia', 'Eastern Europe'),
    208: ('DNK', 'Denmark', 'Northern Europe'),
    233: ('EST', 'Estonia', 'Northern Europe'),
    246: ('FIN', 'Finland', 'Northern Europe'),
    250: ('FRA', 'France', 'Western Europe'),
    276: ('DEU', 'Germany', 'Western Europe'),
    300: ('GRC', 'Greece', 'Southern Europe'),
    348: ('HUN', 'Hungary', 'Eastern Europe'),
    352: ('ISL', 'Iceland', 'Northern Europe'),
    372: ('IRL', 'Ireland', 'Northern Europe'),
    380: ('ITA', 'Italy', 'Southern Europe'),
    392: ('JPN', 'Japan', 'Eastern Asia'),
    398: ('KAZ', 'Kazakhstan', 'Central Asia'),
    428: ('LVA', 'Latvia', 'Northern Europe'),
    438: ('LIE', 'Liechtenstein', 'Western Europe'),
    440: ('LTU', 'Lithuania', 'Northern Europe'),
    442: ('LUX', 'Luxembourg', 'Western Europe'),
    470: ('MLT', 'Malta', 'Southern Europe'),
    492: ('MCO', 'Monaco', 'Western Europe'),
    528: ('NLD', 'Netherlands', 'Western Europe'),
    554: ('NZL', 'New Zealand', 'Oceania'),
    578: ('NOR', 'Norway', 'Northern Europe'),
    616: ('POL', 'Poland', 'Eastern Europe'),
    620: ('PRT', 'Portugal', 'Southern Europe'),
    642: ('ROU', 'Romania', 'Eastern Europe'),
    643: ('RUS', 'Russian Federation', 'Eastern Europe'),
    703: ('SVK', 'Slovakia', 'Eastern Europe'),
    705: ('SVN', 'Slovenia', 'Southern Europe'),
    724: ('ESP', 'Spain', 'Southern Europe'),
    752: ('SWE', 'Sweden', 'Northern Europe'),
    756: ('CHE', 'Switzerland', 'Western Europe'),
    792: ('TUR', 'Türkiye', 'Western Asia'),
    804: ('UKR', 'Ukraine', 'Eastern Europe'),
    826: ('GBR', 'United Kingdom', 'Northern Europe'),
    840: ('USA', 'United States', 'Northern America'),
}


def normalize(value):
    """Normalize whitespace and Unicode case without fuzzy matching."""
    return ' '.join(str(value).strip().casefold().split())


NAME_TO_ID = {normalize(v[1]): k for k, v in COUNTRIES.items()}
NAME_TO_ID.update({
    'united kingdom of great britain and northern ireland': 826,
    'united states of america': 840,
    'turkey': 792,
    'czech republic': 203,
    'russia': 643,
})


def read_wide(path, required):
    """Find a sheet/header containing the required columns and all 31 years."""
    for sheet, table in pd.read_excel(path, sheet_name=None, header=None).items():
        for i in range(min(20, len(table))):
            headers = [str(v).strip().removesuffix('.0') for v in table.iloc[i]]
            if set(required + [str(y) for y in YEARS]).issubset(headers):
                data = table.iloc[i + 1:].copy()
                data.columns = headers
                return data.loc[:, required + [str(y) for y in YEARS]]
    raise ValueError(f'No matching wide-format table in {path}')


def merge_sources(gdp_path, ghg_path):
    """Join prepared wide-format source workbooks by numeric country ID and year.

    Explicit name aliases handle different UNFCCC/UNSD labels. EU and other
    aggregates are excluded; unmatched source entities are documented.
    """
    gdp = read_wide(gdp_path, ['CountryID', 'Country', 'IndicatorName'])
    ghg = read_wide(ghg_path, ['Party'])
    gdp = gdp[gdp['IndicatorName'].map(normalize).isin([
        'gross domestic product (gdp)', 'gross domestic product', 'gdp'])].copy()
    gdp['country_id'] = pd.to_numeric(gdp['CountryID'], errors='coerce')
    ghg['country_id'] = ghg['Party'].map(lambda x: NAME_TO_ID.get(normalize(x)))
    gdp = gdp[gdp['country_id'].isin(COUNTRIES)].copy()
    unmatched_ghg = ghg.loc[ghg['country_id'].isna() & ghg['Party'].notna(), 'Party']
    print('Unmatched/excluded GHG labels:', unmatched_ghg.astype(str).tolist())
    ghg = ghg[ghg['country_id'].notna()].copy()
    if gdp['country_id'].duplicated().any() or ghg['country_id'].duplicated().any():
        raise ValueError('Duplicate source country IDs; review before merging.')
    gdp = gdp.melt(id_vars=['country_id', 'Country'], value_vars=list(map(str, YEARS)),
                   var_name='year', value_name='gdp_usd')
    ghg = ghg.melt(id_vars=['country_id', 'Party'], value_vars=list(map(str, YEARS)),
                   var_name='year', value_name='ghg_kt_co2e')
    merged = gdp.merge(ghg, on=['country_id', 'year'], how='outer',
                       validate='one_to_one', indicator=True)
    if not merged['_merge'].eq('both').all():
        raise ValueError('Some expected country-year keys are unmatched.')
    merged = merged.rename(columns={'Country': 'country', 'Party': 'ghg_source_name'})
    merged['data_status'] = 'Matched'
    return merged.drop(columns='_merge')


def load_merged(path):
    """Use Herak's merged workbook as a fallback; not proof of raw-source merge."""
    df = pd.read_excel(path, sheet_name='Merged Data')
    return df.rename(columns={
        'CountryID (UNSD)': 'country_id', 'Country': 'country',
        'GHG source country name': 'ghg_source_name', 'Year': 'year',
        'GDP (constant 2020 USD)': 'gdp_usd',
        'GHG (kt CO2e, excl LULUCF)': 'ghg_kt_co2e',
        'Data status': 'data_status'})


def load_snapshot(path=None):
    """Read a valid CSV supplied locally, or fetch the pinned historical Git blob."""
    if path is not None:
        return pd.read_csv(path)
    local = ROOT / 'clean_ghg_gdp.csv'
    if local.exists() and local.read_bytes().startswith(b'country_id,'):
        return pd.read_csv(local)
    with urllib.request.urlopen(SNAPSHOT, timeout=30) as response:
        content = response.read()
    git_sha = hashlib.sha1(f'blob {len(content)}\0'.encode() + content).hexdigest()
    if git_sha != SNAPSHOT_BLOB_SHA:
        raise ValueError('Downloaded snapshot does not match the pinned Git blob.')
    from io import BytesIO
    return pd.read_csv(BytesIO(content))


def change(start, end):
    return 100 * (end / start - 1)


def classify(gdp, ghg):
    """Sign-based decoupling classification; a zero GDP change is non-growth."""
    if pd.isna(gdp) or pd.isna(ghg):
        return 'Not available'
    if gdp > 0:
        if ghg < 0:
            return 'Absolute decoupling'
        if ghg < gdp:
            return 'Relative decoupling'
        if ghg == gdp:
            return 'Coupled'
        return 'Emissions growth exceeds GDP growth'
    if ghg < 0:
        return 'GDP non-growth and falling emissions'
    return 'GDP non-growth and non-falling emissions'


def prepare(df):
    """Validate the balanced panel and recompute derived variables."""
    df = df.copy()
    for col in ['country_id', 'year', 'gdp_usd', 'ghg_kt_co2e']:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    if df[['country_id', 'year', 'gdp_usd', 'ghg_kt_co2e']].isna().any().any():
        raise ValueError('Missing required values; do not replace them with zero.')
    if (df[['gdp_usd', 'ghg_kt_co2e']] <= 0).any().any():
        raise ValueError('Non-positive GDP or GHG values.')
    if not np.isfinite(df[['gdp_usd', 'ghg_kt_co2e']].to_numpy()).all():
        raise ValueError('Non-finite GDP or GHG values.')
    if df.duplicated(['country_id', 'year']).any():
        raise ValueError('Duplicate country-year keys.')
    expected = pd.MultiIndex.from_product([COUNTRIES, YEARS])
    observed = pd.MultiIndex.from_frame(df[['country_id', 'year']])
    if len(expected.difference(observed)) or len(observed.difference(expected)):
        raise ValueError('Panel differs from the expected 43 countries × 31 years.')
    df['country_id'] = df['country_id'].astype(int)
    df['year'] = df['year'].astype(int)
    df['iso3'] = df['country_id'].map(lambda x: COUNTRIES[x][0])
    df['country'] = df['country_id'].map(lambda x: COUNTRIES[x][1])
    df['region'] = df['country_id'].map(lambda x: COUNTRIES[x][2])
    df = df.sort_values(['country_id', 'year']).reset_index(drop=True)
    group = df.groupby('country_id')
    df['gdp_growth_pct'] = group['gdp_usd'].pct_change(fill_method=None) * 100
    df['ghg_change_pct'] = group['ghg_kt_co2e'].pct_change(fill_method=None) * 100
    df['gdp_billion_usd'] = df['gdp_usd'] / 1e9
    df['ghg_mt_co2e'] = df['ghg_kt_co2e'] / 1e3
    df['ghg_intensity_kt_per_billion_usd'] = df['ghg_kt_co2e'] / df['gdp_billion_usd']
    df['gdp_index_1990'] = 100 * df['gdp_usd'] / group['gdp_usd'].transform('first')
    df['ghg_index_1990'] = 100 * df['ghg_kt_co2e'] / group['ghg_kt_co2e'].transform('first')
    df['decoupling_category'] = [classify(x, y) for x, y in zip(
        df['gdp_growth_pct'], df['ghg_change_pct'])]
    df['large_annual_change_flag'] = ((df['gdp_growth_pct'].abs() > 25) |
                                     (df['ghg_change_pct'].abs() > 25))
    return df


PERIODS = [(1990, 2020), (1990, 2019), (1990, 2000), (2000, 2010), (2010, 2020)]


def period_summary(df, key):
    """Use endpoints of summed GDP and GHG (not means of growth rates)."""
    rows = []
    for label, group in df.groupby(key):
        for start, end in PERIODS:
            a = group[group.year.eq(start)]
            b = group[group.year.eq(end)]
            g0, g1 = a.gdp_usd.sum(), b.gdp_usd.sum()
            e0, e1 = a.ghg_kt_co2e.sum(), b.ghg_kt_co2e.sum()
            g, h = change(g0, g1), change(e0, e1)
            rows.append({key: label, 'country_count': group.country_id.nunique(),
                         'start_year': start, 'end_year': end,
                         'gdp_change_pct': g, 'ghg_change_pct': h,
                         'intensity_change_pct': change(e0 / g0, e1 / g1),
                         'decoupling_elasticity': h / g if abs(g) > 1e-9 else np.nan,
                         'decoupling_category': classify(g, h)})
    return pd.DataFrame(rows)


def annual_aggregate(df, key):
    """Annual regional or sample totals and indices, for the dashboard."""
    out = df.groupby([key, 'year'], as_index=False).agg(
        gdp_usd=('gdp_usd', 'sum'), ghg_kt_co2e=('ghg_kt_co2e', 'sum'),
        country_count=('country_id', 'nunique'))
    out = out.sort_values([key, 'year'])
    group = out.groupby(key)
    out['gdp_growth_pct'] = group.gdp_usd.pct_change(fill_method=None) * 100
    out['ghg_change_pct'] = group.ghg_kt_co2e.pct_change(fill_method=None) * 100
    out['gdp_index_1990'] = 100 * out.gdp_usd / group.gdp_usd.transform('first')
    out['ghg_index_1990'] = 100 * out.ghg_kt_co2e / group.ghg_kt_co2e.transform('first')
    out['ghg_intensity_kt_per_billion_usd'] = out.ghg_kt_co2e / (out.gdp_usd / 1e9)
    return out


def regression(df):
    """Course-style centered least-squares regression and error measures.

    Pooled annual country observations are not independent. Report descriptive
    association only; no causal claims or naive significance tests.
    """
    data = df[['gdp_growth_pct', 'ghg_change_pct']].dropna()
    x = data.gdp_growth_pct.to_numpy()
    y = data.ghg_change_pct.to_numpy()
    xc, yc = x - x.mean(), y - y.mean()
    slope = (xc @ yc) / (xc @ xc)
    intercept = y.mean() - slope * x.mean()
    predicted = intercept + slope * x
    residual = y - predicted
    return {'n': len(x), 'mean_gdp': x.mean(), 'mean_ghg': y.mean(),
            'sd_gdp': x.std(ddof=1), 'sd_ghg': y.std(ddof=1),
            'covariance': np.cov(x, y, ddof=1)[0, 1],
            'pearson_r': np.corrcoef(x, y)[0, 1], 'slope': slope,
            'intercept': intercept,
            'r2': 1 - (residual @ residual) / (yc @ yc),
            'rmse': np.sqrt(np.mean(residual ** 2)), 'mae': np.mean(np.abs(residual))}


def run(df, output):
    output.mkdir(parents=True, exist_ok=True)
    df = prepare(df)
    df['sample'] = 'All 43 countries'
    country = period_summary(df, 'country').merge(
        df[['country', 'iso3', 'region', 'country_id']].drop_duplicates(),
        on='country', validate='many_to_one')
    region = period_summary(df, 'region')
    total = period_summary(df, 'sample')
    counts = country.groupby(['start_year', 'end_year', 'decoupling_category'],
                             as_index=False).size().rename(columns={'size': 'countries'})
    model = pd.DataFrame([
        {'period': '1991-2020', **regression(df)},
        {'period': '1991-2019', **regression(df[df.year < 2020])}])
    columns = ['gdp_billion_usd', 'ghg_mt_co2e', 'gdp_growth_pct', 'ghg_change_pct',
               'ghg_intensity_kt_per_billion_usd']
    tables = {'annual_country': df.drop(columns='sample'), 'country_decoupling': country,
              'regional_decoupling': region, 'sample_decoupling': total,
              'decoupling_counts': counts, 'annual_region': annual_aggregate(df, 'region'),
              'annual_sample': annual_aggregate(df, 'sample'), 'regression_results': model,
              'descriptive_statistics': df[columns].describe().T.reset_index(names='variable'),
              'correlation_matrix': df[columns].corr().reset_index(names='variable'),
              'large_annual_changes': df[df.large_annual_change_flag].drop(columns='sample')}
    for name, table in tables.items():
        table.to_csv(output / f'{name}.csv', index=False, float_format='%.10g')
    checks = {'rows': len(df), 'countries': df.country_id.nunique(),
              'year_min': int(df.year.min()), 'year_max': int(df.year.max()),
              'duplicate_keys': int(df.duplicated(['country_id', 'year']).sum()),
              'annual_change_pairs': int(df.gdp_growth_pct.notna().sum())}
    (output / 'validation.json').write_text(json.dumps(checks, indent=2) + '\n')
    return tables


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', choices=['raw', 'snapshot', 'merged'], default='snapshot')
    parser.add_argument('--merged', type=Path, default=ROOT / 'Merged files.xlsx')
    parser.add_argument('--gdp', type=Path, default=ROOT / 'GPD.xlsx')
    parser.add_argument('--ghg', type=Path, default=ROOT / 'GHG.xlsx')
    parser.add_argument('--input', type=Path, help='Optional local cleaned CSV')
    parser.add_argument('--output', type=Path, default=HERE / 'results')
    args = parser.parse_args()
    if args.source == 'raw':
        df = merge_sources(args.gdp, args.ghg)
    elif args.source == 'merged':
        df = load_merged(args.merged)
    else:
        df = load_snapshot(args.input)
    tables = run(df, args.output)
    print(tables['regression_results'].to_string(index=False))
    print(f'Wrote {len(tables)} tables to {args.output}')


if __name__ == '__main__':
    main()
