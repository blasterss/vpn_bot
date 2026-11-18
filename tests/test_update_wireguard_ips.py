import os
import stat
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import update_wireguard_ips as updater


class AddressTests(unittest.TestCase):
    def test_parse_mixed_list(self):
        text = "Meta\n// Hosts\n1.2.3.4, 1.2.3.4/32\n// Networks\n10.0.0.7/24"
        self.assertEqual(updater.parse_addresses(text), ["1.2.3.4/32", "10.0.0.0/24"])

    def test_reject_empty_or_invalid_addresses(self):
        for text in ("<html>error</html>", "", "999.1.1.1", "1.2.3.4/33"):
            with self.subTest(text=text), self.assertRaises(ValueError):
                updater.parse_addresses(text)

    def test_windows_routes_do_not_import_masks_or_gateways(self):
        text = (
            "route ADD 8.8.8.0 MASK 255.255.255.0 0.0.0.0\n"
            "route ADD 9.9.9.9 MASK 255.255.255.255 192.168.1.1\n"
            "8.8.8.8/32\n# Example 0.0.0.0/0\n"
        )
        self.assertEqual(updater.parse_addresses(text), ["8.8.8.0/24", "9.9.9.9/32"])

    def test_reject_invalid_windows_netmask(self):
        with self.assertRaises(ValueError):
            updater.parse_addresses("route ADD 8.8.8.0 MASK 255.0.255.0 0.0.0.0")

    def test_env_url_and_cli_override(self):
        for args, expected in (
            ([], "https://example.com/env"),
            (["--url", "https://example.com/cli"], "https://example.com/cli"),
        ):
            with patch.dict(os.environ, {"SOURCE_URL": "https://example.com/env"}):
                with patch("sys.argv", ["updater", *args]):
                    with patch.object(
                        updater, "download_addresses", return_value=["1.2.3.4/32"]
                    ) as download:
                        with patch.object(updater, "update_params", return_value=True):
                            updater.main()
                    download.assert_called_once_with(expected)


class ParamsTests(unittest.TestCase):
    def test_preserve_settings_permissions_and_skip_unchanged(self):
        with tempfile.TemporaryDirectory() as directory:
            params = Path(directory) / "params"
            params.write_text(
                "SERVER_PRIV_KEY=secret\nALLOWED_IPS=0.0.0.0/0,::/0\nSERVER_PORT=123\n"
            )
            params.chmod(0o600)
            previous = params.stat()
            self.assertTrue(updater.update_params(params, ["1.2.3.4/32"]))
            self.assertEqual(
                params.read_text(),
                "SERVER_PRIV_KEY=secret\nALLOWED_IPS=1.2.3.4/32\nSERVER_PORT=123\n",
            )
            current = params.stat()
            self.assertEqual(stat.S_IMODE(current.st_mode), 0o600)
            self.assertEqual((current.st_uid, current.st_gid), (previous.st_uid, previous.st_gid))
            self.assertFalse(updater.update_params(params, ["1.2.3.4/32"]))
            self.assertEqual(params.stat().st_ino, current.st_ino)

    def test_failed_replace_leaves_original_and_no_temporary_file(self):
        with tempfile.TemporaryDirectory() as directory:
            params = Path(directory) / "params"
            original = "ALLOWED_IPS=0.0.0.0/0\n"
            params.write_text(original)
            with patch.object(updater.os, "replace", side_effect=OSError("disk error")):
                with self.assertRaises(OSError):
                    updater.update_params(params, ["1.2.3.4/32"])
            self.assertEqual(params.read_text(), original)
            self.assertEqual(
                sorted(p.name for p in Path(directory).iterdir()),
                ["params", "params.ips-update.lock"],
            )

    def test_reject_missing_or_duplicate_setting(self):
        for original in ("SERVER_PORT=123\n", "ALLOWED_IPS=a\nALLOWED_IPS=b\n"):
            with tempfile.TemporaryDirectory() as directory:
                params = Path(directory) / "params"
                params.write_text(original)
                with self.assertRaises(ValueError):
                    updater.update_params(params, ["1.2.3.4/32"])
                self.assertEqual(params.read_text(), original)
