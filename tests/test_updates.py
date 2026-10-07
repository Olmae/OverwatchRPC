import unittest
from owrpc_app.updates import select_release, check_release


class ReleaseTests(unittest.TestCase):
    def release(self, tag, **kwargs):
        return {"tag_name": tag, "draft": False, "prerelease": "-" in tag, **kwargs}

    def test_beta_versions_compare_numerically_and_ignore_drafts(self):
        rows = [self.release("v2.0.0-beta.10"), self.release("v9.0.0", draft=True), self.release("bad")]
        result = select_release(rows, "2.0.0-beta.3")
        self.assertEqual(result.version, "2.0.0-beta.10")
        self.assertEqual(result.url, "https://github.com/Olmae/OverwatchRPC/releases/tag/v2.0.0-beta.10")

    def test_stable_channel_excludes_prereleases_and_old_versions(self):
        self.assertIsNone(select_release([self.release("v2.1.0-beta.1"), self.release("v2.0.0")], "2.0.0"))
        result = select_release([self.release("v2.0.0-beta.20"), self.release("v2.0.0")], "2.0.0-beta.3")
        self.assertEqual(result.version, "2.0.0")
        self.assertIsNone(select_release([], "2.0.0"))

    def test_invalid_response_fails_instead_of_claiming_up_to_date(self):
        with self.assertRaises(ValueError):
            select_release({"message": "API rate limit"}, "2.0.0")
        with self.assertRaises(ValueError):
            select_release([], "unknown")
        with self.assertRaises(OSError):
            check_release("2.0.0", fetch=lambda _: (_ for _ in ()).throw(OSError("offline")))


if __name__ == "__main__":
    unittest.main()
