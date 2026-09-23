"""Chronological evaluation of a pre-call bank marketing response model."""
from __future__ import annotations

import io
import json
import urllib.request
import zipfile
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.dummy import DummyClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (average_precision_score, brier_score_loss,
                             precision_recall_curve, roc_auc_score)
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

SOURCE = 'https://archive.ics.uci.edu/static/public/222/bank+marketing.zip'
NUMERIC = ['age', 'campaign', 'pdays', 'previous', 'emp.var.rate',
           'cons.price.idx', 'cons.conf.idx', 'euribor3m', 'nr.employed']
CATEGORICAL = ['job', 'education', 'housing', 'loan', 'contact',
               'month', 'day_of_week', 'poutcome']
FEATURES = NUMERIC + CATEGORICAL
EXCLUDED = {'duration', 'y', 'marital', 'default'}


def download_data(url: str = SOURCE) -> tuple[pd.DataFrame, str]:
    with urllib.request.urlopen(url, timeout=60) as response:
        archive = response.read()
    import hashlib
    with zipfile.ZipFile(io.BytesIO(archive)) as outer:
        with zipfile.ZipFile(io.BytesIO(outer.read('bank-additional.zip'))) as inner:
            with inner.open('bank-additional/bank-additional-full.csv') as f:
                df = pd.read_csv(f, sep=';')
    return df, hashlib.sha256(archive).hexdigest()


def check_data(df: pd.DataFrame) -> dict:
    expected = set(FEATURES) | EXCLUDED
    if set(df.columns) != expected:
        raise ValueError(f'Unexpected columns: {set(df.columns) ^ expected}')
    if df.empty or df[FEATURES].isna().any().any():
        raise ValueError('Empty table or missing features')
    if not df.y.isin(['yes', 'no']).all():
        raise ValueError('Invalid target')
    if (df['duration'] < 0).any() or (df['campaign'] < 1).any():
        raise ValueError('Invalid call counts or duration')
    return {'rows': len(df), 'columns': len(df.columns),
            'positive_count': int((df.y == 'yes').sum()),
            'positive_rate': round(float((df.y == 'yes').mean()), 5)}


def split_positions(n: int) -> tuple[slice, slice, slice]:
    if n < 10:
        raise ValueError('Too few observations')
    # Dataset documentation says rows are ordered by date; exact dates are absent.
    return slice(0, int(.64*n)), slice(int(.64*n), int(.8*n)), slice(int(.8*n), n)


def preprocessor() -> ColumnTransformer:
    return ColumnTransformer([
        ('numeric', make_pipeline(SimpleImputer(strategy='median'), StandardScaler()), NUMERIC),
        ('categorical', make_pipeline(SimpleImputer(strategy='most_frequent'),
                                    OneHotEncoder(handle_unknown='ignore')), CATEGORICAL),
    ])


def metrics(y: pd.Series, probability: np.ndarray) -> dict:
    return {'average_precision': round(float(average_precision_score(y, probability)), 4),
            'roc_auc': round(float(roc_auc_score(y, probability)), 4),
            'brier': round(float(brier_score_loss(y, probability)), 4)}


def top_fraction(y: pd.Series, probability: np.ndarray, fraction: float = .10) -> dict:
    count = max(1, int(np.ceil(len(y) * fraction)))
    selected = np.argsort(-probability, kind='stable')[:count]
    actual = np.asarray(y)[selected]
    return {'selected': count, 'responses': int(actual.sum()),
            'precision': round(float(actual.mean()), 4),
            'recall': round(float(actual.sum() / y.sum()), 4)}


def run(output: Path) -> dict:
    output.mkdir(parents=True, exist_ok=True)
    df, digest = download_data()
    quality = check_data(df)
    quality['source_zip_sha256'] = digest
    y = (df.y == 'yes').astype(int)
    train, validation, test = split_positions(len(df))
    X = df[FEATURES]
    candidate_results = []
    for C in (.01, .1, 1.0):
        model = make_pipeline(preprocessor(), LogisticRegression(C=C, max_iter=1000))
        model.fit(X.iloc[train], y.iloc[train])
        score = average_precision_score(y.iloc[validation], model.predict_proba(X.iloc[validation])[:, 1])
        candidate_results.append({'C': C, 'validation_average_precision': round(float(score), 4)})
    best = max(candidate_results, key=lambda r: r['validation_average_precision'])['C']
    model = make_pipeline(preprocessor(), LogisticRegression(C=best, max_iter=1000))
    model.fit(X.iloc[:test.start], y.iloc[:test.start])
    p = model.predict_proba(X.iloc[test])[:, 1]
    baseline = DummyClassifier(strategy='prior')
    baseline.fit(X.iloc[:test.start], y.iloc[:test.start])
    p0 = baseline.predict_proba(X.iloc[test])[:, 1]
    names = model.named_steps['columntransformer'].get_feature_names_out()
    coefficients = model.named_steps['logisticregression'].coef_[0]
    terms = sorted(zip(names, coefficients), key=lambda t: abs(t[1]), reverse=True)[:12]
    result = {'quality': quality, 'split': {
        'train': train.stop, 'validation': validation.stop - validation.start,
        'test': len(y) - test.start,
        'train_positive_rate': round(float(y.iloc[train].mean()), 4),
        'validation_positive_rate': round(float(y.iloc[validation].mean()), 4),
        'test_positive_rate': round(float(y.iloc[test].mean()), 4)},
        'selection': candidate_results, 'selected_C': best,
        'baseline': metrics(y.iloc[test], p0), 'model': metrics(y.iloc[test], p),
        'top_decile': top_fraction(y.iloc[test], p),
        'largest_absolute_coefficients': [{'term': str(n), 'log_odds_coefficient': round(float(c), 3)} for n,c in terms]}
    (output / 'results.json').write_text(json.dumps(result, indent=2) + '\n')
    precision, recall, _ = precision_recall_curve(y.iloc[test], p)
    fig, ax = plt.subplots(figsize=(7, 5))
    ax.plot(recall, precision, label=f'Logistic regression (AP={result["model"]["average_precision"]:.3f})')
    ax.axhline(y.iloc[test].mean(), color='gray', ls='--', label='Test prevalence / constant baseline')
    ax.set(xlabel='Recall', ylabel='Precision', title='Held-out chronological segment: response prediction',
           xlim=(0, 1), ylim=(0, 1))
    ax.legend()
    fig.tight_layout()
    fig.savefig(output / 'precision_recall.svg')
    plt.close(fig)
    return result


if __name__ == '__main__':
    print(json.dumps(run(Path(__file__).parent / 'outputs'), indent=2))
