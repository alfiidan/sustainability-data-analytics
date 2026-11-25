"""Synthetic-data tests; no project results are fabricated by these fixtures."""
from pathlib import Path
import sys
import tempfile
import unittest

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from analysis import COUNTRIES, YEARS, classify, merge_sources, prepare, run


class AnalysisTests(unittest.TestCase):
    def fixture(self):
        rows = []
        for i, (code, (_, name, _)) in enumerate(COUNTRIES.items()):
            for year in YEARS:
                t = year - 1990
                growth = 1.01 + (i % 5) * .006
                # Vary changes across countries and years.
                gdp = (i + 1) * 1e9 * growth ** t
                ghg = (i + 1) * 1e3 * (.99 + (i % 4) * .007) ** t
                rows.append([code, name, year, gdp, ghg])
        return pd.DataFrame(rows, columns=['country_id', 'country', 'year',
                                           'gdp_usd', 'ghg_kt_co2e'])

    def test_classification(self):
        self.assertEqual(classify(5, -1), 'Absolute decoupling')
        self.assertEqual(classify(5, 2), 'Relative decoupling')
        self.assertEqual(classify(5, 5), 'Coupled')
        self.assertEqual(classify(5, 7), 'Emissions growth exceeds GDP growth')
        self.assertEqual(classify(-2, -4), 'GDP non-growth and falling emissions')
        self.assertEqual(classify(0, 2), 'GDP non-growth and non-falling emissions')
        self.assertEqual(classify(np.nan, 2), 'Not available')

    def test_panel(self):
        df = prepare(self.fixture())
        self.assertEqual(len(df), 1333)
        self.assertEqual(df.iso3.nunique(), 43)
        self.assertEqual(df.gdp_growth_pct.notna().sum(), 1290)
        self.assertTrue(df.loc[df.year.eq(1990), 'gdp_index_1990'].eq(100).all())
        with self.assertRaises(ValueError):
            prepare(pd.concat([df, df.iloc[:1]]))
        with self.assertRaises(ValueError):
            prepare(df.iloc[:-1])

    def test_merge_and_full_pipeline(self):
        panel = self.fixture()
        gdp = panel.pivot(index=['country_id', 'country'], columns='year',
                          values='gdp_usd').reset_index().rename(
                              columns={'country_id': 'CountryID', 'country': 'Country'})
        gdp['IndicatorName'] = 'Gross Domestic Product (GDP)'
        ghg = panel.pivot(index='country', columns='year', values='ghg_kt_co2e')
        ghg = ghg.reset_index().rename(columns={'country': 'Party'})
        ghg['Party'] = ghg['Party'].replace({'United States': 'United States of America',
            'United Kingdom': 'United Kingdom of Great Britain and Northern Ireland'})
        ghg.loc[len(ghg)] = ['European Union'] + [999] * 31
        with tempfile.TemporaryDirectory() as td:
            path = Path(td)
            gdp.to_excel(path / 'gdp.xlsx', index=False)
            ghg.to_excel(path / 'ghg.xlsx', index=False)
            merged = merge_sources(path / 'gdp.xlsx', path / 'ghg.xlsx')
            self.assertEqual(len(merged), 1333)
            output = run(merged, path / 'results')
            self.assertEqual(len(output['country_decoupling']), 215)
            self.assertEqual(len(output['regional_decoupling']), 45)
            self.assertEqual(len(output['annual_region']), 279)
            self.assertEqual(output['regression_results']['n'].tolist(), [1290, 1247])
            self.assertTrue((path / 'results' / 'validation.json').exists())


if __name__ == '__main__':
    unittest.main()
