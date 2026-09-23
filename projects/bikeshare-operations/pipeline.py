"""Reproduce a descriptive Capital Bikeshare operations analysis from UCI data."""
from __future__ import annotations

import argparse
import csv
import io
import json
import sqlite3
import urllib.request
import zipfile
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

SOURCE = 'https://archive.ics.uci.edu/static/public/275/bike+sharing+dataset.zip'
COLUMNS = ('instant', 'dteday', 'season', 'yr', 'mnth', 'hr', 'holiday',
           'weekday', 'workingday', 'weathersit', 'temp', 'atemp', 'hum',
           'windspeed', 'casual', 'registered', 'cnt')


def download_rows(url: str = SOURCE) -> tuple[list[dict], bytes]:
    with urllib.request.urlopen(url, timeout=60) as response:
        archive = response.read()
    with zipfile.ZipFile(io.BytesIO(archive)) as z:
        with z.open('hour.csv') as handle:
            rows = list(csv.DictReader(io.TextIOWrapper(handle, encoding='utf-8-sig')))
    return rows, archive


def check_rows(rows: list[dict]) -> dict:
    if not rows:
        raise ValueError('No hourly observations')
    if tuple(rows[0]) != COLUMNS:
        raise ValueError('Unexpected schema')
    ids, hours = set(), set()
    for row in rows:
        idx = int(row['instant'])
        day = row['dteday']
        hour = int(row['hr'])
        key = (day, hour)
        if idx in ids or key in hours:
            raise ValueError(f'Duplicate observation: {key}')
        ids.add(idx)
        hours.add(key)
        if not 0 <= hour <= 23 or int(row['workingday']) not in (0, 1):
            raise ValueError(f'Invalid hour/day type: {key}')
        if min(int(row['cnt']), int(row['casual']), int(row['registered'])) < 0:
            raise ValueError(f'Negative rental count: {key}')
        if int(row['casual']) + int(row['registered']) != int(row['cnt']):
            raise ValueError(f'Count components disagree: {key}')
    return {'rows': len(rows), 'unique_dates': len({r['dteday'] for r in rows}),
            'first_date': min(r['dteday'] for r in rows),
            'last_date': max(r['dteday'] for r in rows),
            'missing_date_hour_combinations':
                (len({r['dteday'] for r in rows}) * 24 - len(rows))}


SCHEMA = '''CREATE TABLE hourly (
    observation_id INTEGER PRIMARY KEY, date TEXT NOT NULL, hour INTEGER NOT NULL,
    working_day INTEGER NOT NULL, holiday INTEGER NOT NULL,
    weather_code INTEGER NOT NULL, casual INTEGER NOT NULL,
    registered INTEGER NOT NULL, rentals INTEGER NOT NULL,
    UNIQUE(date, hour), CHECK(hour BETWEEN 0 AND 23),
    CHECK(rentals = casual + registered)
);'''


def load_database(rows: list[dict], path: Path) -> None:
    if path.exists():
        path.unlink()
    with sqlite3.connect(path) as db:
        db.execute(SCHEMA)
        db.executemany('INSERT INTO hourly VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)', [
            (int(r['instant']), r['dteday'], int(r['hr']), int(r['workingday']),
             int(r['holiday']), int(r['weathersit']), int(r['casual']),
             int(r['registered']), int(r['cnt'])) for r in rows])


def query_to_csv(db: sqlite3.Connection, sql: str, path: Path) -> list[dict]:
    cursor = db.execute(sql)
    data = [dict(zip([c[0] for c in cursor.description], row)) for row in cursor]
    with path.open('w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=[c[0] for c in cursor.description])
        writer.writeheader()
        writer.writerows(data)
    return data


def run(output: Path, url: str = SOURCE) -> dict:
    output.mkdir(parents=True, exist_ok=True)
    rows, archive = download_rows(url)
    checks = check_rows(rows)
    import hashlib
    checks['source_zip_sha256'] = hashlib.sha256(archive).hexdigest()
    (output / 'quality.json').write_text(json.dumps(checks, indent=2) + '\n')
    db_path = output / 'bikeshare.sqlite'
    load_database(rows, db_path)
    sql = (Path(__file__).parent / 'analysis.sql').read_text().split('-- QUERY:')
    sql = [part.split('\n', 1)[1] for part in sql[1:]]
    with sqlite3.connect(db_path) as db:
        profiles = query_to_csv(db, sql[0], output / 'hourly_profiles.csv')
        peaks = query_to_csv(db, sql[1], output / 'peak_hours.csv')
    fig, ax = plt.subplots(figsize=(9, 5))
    for code, label in [(1, 'Working day'), (0, 'Nonworking day')]:
        subset = sorted((r for r in profiles if r['working_day'] == code), key=lambda x: x['hour'])
        ax.plot([r['hour'] for r in subset], [r['mean_rentals'] for r in subset],
                marker='o', ms=3, label=label)
    ax.set(xlabel='Hour of day', ylabel='Mean rentals per observed hour',
           title='Capital Bikeshare: hourly demand by day type (2011–2012)', xticks=range(0, 24, 2))
    ax.legend()
    ax.grid(alpha=.2)
    fig.tight_layout()
    fig.savefig(output / 'hourly_profiles.svg')
    plt.close(fig)
    return {'quality': checks, 'peaks': peaks}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, default=Path(__file__).parent / 'outputs')
    args = parser.parse_args()
    print(json.dumps(run(args.output), indent=2))
