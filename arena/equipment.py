"""Translate pinned game catalogs to the IDs accepted by the generator API."""
from .core import read_json


def catalog(data, kind):
    raw = read_json(data / (kind + '.json'))
    return {str(row['item'] if kind == 'weapons' else key):
            {**row, 'catalog_key': key, 'runtime_id': int(row['item'] if kind == 'weapons' else key)}
            for key, row in raw.items()}
