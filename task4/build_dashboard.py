"""Task 4: build an offline interactive HTML dashboard from Task 3 outputs.
Run from anywhere; point --repo at the checked-out QJ8W7I-task-3 repository.
"""
from pathlib import Path
import argparse
import importlib.util
import json
import sys
import pandas as pd

HERE = Path(__file__).resolve().parent


def load_analysis(repo):
    path = repo / 'analysis.py'
    if not path.is_file():
        path = repo / 'task3' / 'analysis.py'
    if not path.is_file():
        raise FileNotFoundError('analysis.py not found. Check out QJ8W7I-task-3 first.')
    spec = importlib.util.spec_from_file_location('task3_analysis', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def build(repo, source, output, results_dir, snapshot=None):
    analysis = load_analysis(repo)
    if source == 'raw':
        df = analysis.merge_sources(repo / 'GPD.xlsx', repo / 'GHG.xlsx')
    elif source == 'snapshot':
        df = analysis.load_snapshot(snapshot)
    else:
        df = analysis.load_merged(repo / 'Merged files.xlsx')
    # Call the original Task 3 code directly; do not copy or replace its analysis.
    tables = analysis.run(df, results_dir)
    needed = ['annual_country','country_decoupling','regional_decoupling',
              'sample_decoupling','annual_region','annual_sample','regression_results',
              'decoupling_counts','descriptive_statistics','correlation_matrix','large_annual_changes']
    payload = {name: json.loads(tables[name].to_json(orient='records', double_precision=15)) for name in needed}
    payload['validation'] = json.loads((results_dir / 'validation.json').read_text())
    # Escape script closing sequences and Unicode separators in embedded JSON.
    data = json.dumps(payload, ensure_ascii=True, separators=(',', ':'), allow_nan=False).replace('<', '\\u003c')
    template = (HERE / 'dashboard_template.html').read_text(encoding='utf-8')
    marker = '/*__PYTHON_RESULTS__*/null'
    if template.count(marker) != 1:
        raise ValueError('Template payload marker missing or duplicated.')
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(template.replace(marker, data), encoding='utf-8')
    print(f'Created {output} ({len(tables["annual_country"])} records)')
    print(f'Task 3 outputs: {results_dir}')
    print(tables['regression_results'].to_string(index=False))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--repo', type=Path, default=Path.cwd())
    p.add_argument('--source', choices=['merged','raw','snapshot'], default='merged')
    p.add_argument('--snapshot', type=Path, help='Optional local historical cleaned CSV')
    p.add_argument('--output', type=Path, default=Path('sustainability_dashboard.html'))
    p.add_argument('--results', type=Path, default=Path('dashboard_results'))
    args = p.parse_args()
    build(args.repo.resolve(), args.source, args.output.resolve(), args.results.resolve(), args.snapshot)


if __name__ == '__main__':
    main()
