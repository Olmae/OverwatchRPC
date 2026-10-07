import unittest

from owrpc_app.catalog import load_catalog, resource_dir
from owrpc_app.model import match_catalog


class CatalogTests(unittest.TestCase):
    def test_snapshot_includes_official_new_roster(self):
        catalog = load_catalog()
        self.assertEqual(catalog["as_of"], "2026-10-06")
        self.assertEqual(len(catalog["heroes"]), 54)
        self.assertEqual(len(catalog["maps"]), 59)
        names = {h["name"] for h in catalog["heroes"]}
        self.assertTrue({"Doctrine", "D.Mon", "Shion", "Jetpack Cat", "Wuyang"}.issubset(names))
        for hero in catalog["heroes"]:
            self.assertTrue(hero["image_available"], hero["name"])
            self.assertTrue((resource_dir() / "heroes" / (hero["key"] + ".png")).exists())

    def test_every_exact_name_can_be_recognized(self):
        catalog = load_catalog()
        for kind in ("heroes", "maps"):
            names = [r["name"] for r in catalog[kind]]
            for name in names:
                self.assertEqual(match_catalog(name, names), name)


if __name__ == "__main__":
    unittest.main()
