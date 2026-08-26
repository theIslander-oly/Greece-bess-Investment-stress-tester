from __future__ import annotations

import unittest

from greek_bess.data.http import OfficialDataDownloadError, validate_https_url


class OfficialDataHttpTests(unittest.TestCase):
    def test_https_allowlist_accepts_expected_host(self) -> None:
        result = validate_https_url(
            "https://www.admie.gr/getFiletypeInfoEN#fragment",
            allowed_hosts={"www.admie.gr"},
        )
        self.assertEqual(result, "https://www.admie.gr/getFiletypeInfoEN")

    def test_credentials_http_and_foreign_hosts_are_rejected(self) -> None:
        for url in (
            "http://www.admie.gr/file.xls",
            "https://token@www.admie.gr/file.xls",
            "https://example.com/file.xls",
        ):
            with self.subTest(url=url):
                with self.assertRaises(OfficialDataDownloadError):
                    validate_https_url(url, allowed_hosts={"www.admie.gr"})


if __name__ == "__main__":
    unittest.main()

