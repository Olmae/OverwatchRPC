from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from owrpc_app.catalog import load_catalog
from owrpc_app.catalog_updates import refresh_catalog


class CatalogUpdateTests(unittest.TestCase):
    def setUp(self):
        self.base = load_catalog()
        self.html = ''.join(f'<a class="hero-card" id="{h["key"]}" data-role="{h["role"]}" href="/heroes/{h["key"]}"><img class="heroCardPortrait" src="{h["portrait"]}"><h2>{h["name"]}</h2></a>' for h in self.base['heroes'])
        self.html += '<a class="hero-card" id="new-hero" data-role="support" href="/heroes/new-hero"><img class="heroCardPortrait" src="https://example.com/new.png"><h2>New Hero</h2></a>'
        self.maps = deepcopy(self.base['maps'])

    def fetch(self, url):
        return self.html.encode() if 'blizzard' in url else json.dumps(self.maps).encode()

    def test_refresh_preserves_translations_and_loads_offline_cache(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'catalog-cache.json'
            new = refresh_catalog(self.base, path, fetch=self.fetch, now=1000)
            self.assertEqual(len(new['heroes']), len(self.base['heroes']) + 1)
            ana = next(h for h in new['heroes'] if h['key'] == 'ana')
            self.assertEqual(ana['localized_names']['ru'], 'Ана')
            self.assertEqual(len(load_catalog(path)['heroes']), len(new['heroes']))
            self.assertIsNone(refresh_catalog(new, path, fetch=lambda _: self.fail('fresh cache must skip requests'), now=1001))

    def test_partial_or_duplicate_response_does_not_replace_good_cache(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'catalog-cache.json'
            refresh_catalog(self.base, path, fetch=self.fetch, now=1000)
            before = path.read_bytes()
            for html in ('<html>Service unavailable</html>', self.html + self.html):
                with self.assertRaises(ValueError):
                    refresh_catalog(self.base, path, force=True, fetch=lambda url: html.encode() if 'blizzard' in url else json.dumps(self.maps).encode(), now=2000)
                self.assertEqual(path.read_bytes(), before)

    def test_corrupt_cache_falls_back_to_bundled_catalog(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'catalog-cache.json'
            for malformed in ('{broken', '[]', 'null'):
                path.write_text(malformed)
                self.assertEqual(load_catalog(path), self.base)


if __name__ == '__main__':
    unittest.main()
