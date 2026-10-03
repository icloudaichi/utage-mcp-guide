"""Offline regression checks for backup request destinations; no real API key."""

import importlib.util
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlsplit


SCRIPT = Path(__file__).resolve().parents[1] / "backup" / "scripts" / "backup_funnels.py"
SPEC = importlib.util.spec_from_file_location("backup_funnels", SCRIPT)
backup = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(backup)


class BackupDestinationTests(unittest.TestCase):
    def test_config_to_get_request_uses_official_base_once(self):
        """Exercise config loading and Request construction with every old/new form."""
        bases = (
            None,
            "",
            "https://api.utage-system.com",
            "https://api.utage-system.com/",
            "https://api.utage-system.com/v1",
            "https://api.utage-system.com/v1/",
            "https://utage-system.com/api",
            "https://utage-system.com/api/v1",
        )
        for base in bases:
            with self.subTest(base=base), tempfile.TemporaryDirectory() as directory:
                config = Path(directory) / ".env"
                contents = "UTAGE_API_KEY=offline-placeholder\n"
                if base is not None:
                    contents += f"UTAGE_BASE_URL={base}\n"
                config.write_text(contents, encoding="utf-8")
                with patch.object(backup, "ENV_FILE", config):
                    key, api_base = backup.load_config()

                response = io.BytesIO(json.dumps({"data": [], "meta": {
                    "current_page": 2, "per_page": 1, "total": 1
                }}).encode("utf-8"))
                with patch.object(backup, "urlopen", return_value=response) as transport:
                    result = backup.api_get("/funnels", key, api_base, {
                        "page": 2, "per_page": 1, "name": None
                    })

                request = transport.call_args.args[0]
                destination = urlsplit(request.full_url)
                self.assertEqual(destination.scheme, "https")
                self.assertEqual(destination.netloc, "api.utage-system.com")
                self.assertEqual(destination.path, "/v1/funnels")
                self.assertEqual(parse_qs(destination.query), {"page": ["2"], "per_page": ["1"]})
                self.assertEqual(request.get_method(), "GET")
                self.assertIsNone(request.data)
                self.assertEqual(request.get_header("Authorization"), "Bearer offline-placeholder")
                self.assertEqual(result["data"], [])
                transport.assert_called_once()

    def test_explicit_custom_base_remains_configurable(self):
        # Preserve the existing local/proxy configuration feature.
        for base in ("https://example.invalid/api", "https://example.invalid/api/v1/"):
            with self.subTest(base=base):
                self.assertEqual(backup.normalize_api_base(base), "https://example.invalid/api/v1")

    def test_missing_key_exits_before_transport(self):
        with tempfile.TemporaryDirectory() as directory:
            config = Path(directory) / ".env"
            config.write_text("UTAGE_BASE_URL=https://api.utage-system.com/v1\n", encoding="utf-8")
            with patch.object(backup, "ENV_FILE", config), \
                    patch.object(backup, "urlopen") as transport, \
                    patch("sys.stdout", new=io.StringIO()):
                with self.assertRaises(SystemExit) as error:
                    backup.load_config()
                self.assertEqual(error.exception.code, 1)
                transport.assert_not_called()


def listing_page(page, total, data, per_page=1):
    return {"data": data, "meta": {"current_page": page, "per_page": per_page, "total": total}}


class BackupCompletenessTests(unittest.TestCase):
    def test_full_pagination_checks_count(self):
        pages = [listing_page(1, 2, [{"id": "sample-1", "name": "Sample 1"}]),
                 listing_page(2, 2, [{"id": "sample-2", "name": "Sample 2"}])]
        with patch.object(backup, "api_get", side_effect=pages) as transport, \
                patch.object(backup.time, "sleep"):
            data, meta = backup.fetch_all_funnels("offline-placeholder", backup.API_BASE_DEFAULT)
        self.assertEqual(len(data), 2)
        self.assertEqual(meta, {"complete": True, "expected_total": 2, "failure": None})
        self.assertEqual([call.args[3]["page"] for call in transport.call_args_list], [1, 2])

    def test_incomplete_pagination_is_not_zero_success(self):
        first = listing_page(1, 2, [{"id": "sample-1", "name": "Sample 1"}])
        cases = (
            ([None], "api_error"),
            ([{"data": []}], "invalid_pagination"),
            ([{"data": [], "meta": {"current_page": 1, "per_page": 1}}], "invalid_pagination"),
            ([listing_page(True, 0, [])], "invalid_pagination"),
            ([listing_page(1, 1, [])], "count_mismatch"),
            ([first, None], "api_error"),
            ([first, listing_page(2, 3, [])], "pagination_changed"),
            ([first, listing_page(2, 2, [{"id": "sample-1", "name": "Sample 1"}])], "duplicate_resource"),
            ([first, listing_page(1, 2, [])], "invalid_pagination"),
            ([listing_page(1, 1, [{"name": "Missing ID"}])], "invalid_resource"),
        )
        for responses, failure in cases:
            with self.subTest(failure=failure, responses=responses), \
                    patch.object(backup, "api_get", side_effect=responses), \
                    patch.object(backup.time, "sleep"):
                _, meta = backup.fetch_all_funnels("offline-placeholder", backup.API_BASE_DEFAULT)
            self.assertFalse(meta["complete"])
            self.assertEqual(meta["failure"], failure)

    def test_verified_empty_list_is_complete(self):
        with patch.object(backup, "api_get", return_value=listing_page(1, 0, [])):
            data, meta = backup.fetch_all_funnels("offline-placeholder", backup.API_BASE_DEFAULT)
        self.assertEqual(data, [])
        self.assertTrue(meta["complete"])
        self.assertEqual(meta["expected_total"], 0)

    def test_short_first_page_cannot_be_balanced_by_overfull_last_page(self):
        pages = [listing_page(1, 3, [{"id": "sample-1", "name": "Sample 1"}], per_page=2),
                 listing_page(2, 3, [{"id": "sample-2", "name": "Sample 2"},
                                      {"id": "sample-3", "name": "Sample 3"}], per_page=2)]
        with patch.object(backup, "api_get", side_effect=pages) as transport:
            _, meta = backup.fetch_all_funnels("offline-placeholder", backup.API_BASE_DEFAULT)
        self.assertFalse(meta["complete"])
        self.assertEqual(meta["failure"], "count_mismatch")
        transport.assert_called_once()

    def test_final_page_must_match_its_remainder_count(self):
        first = listing_page(1, 3, [{"id": "sample-1", "name": "Sample 1"},
                                   {"id": "sample-2", "name": "Sample 2"}], per_page=2)
        last_data_cases = ([], [{"id": "sample-3", "name": "Sample 3"},
                               {"id": "sample-4", "name": "Sample 4"}])
        for last_data in last_data_cases:
            with self.subTest(last_count=len(last_data)), \
                    patch.object(backup, "api_get", side_effect=[first, listing_page(2, 3, last_data, per_page=2)]), \
                    patch.object(backup.time, "sleep"):
                data, meta = backup.fetch_all_funnels("offline-placeholder", backup.API_BASE_DEFAULT)
            self.assertEqual(len(data), 2)
            self.assertFalse(meta["complete"])
            self.assertEqual(meta["failure"], "count_mismatch")

    def test_main_list_failure_writes_incomplete_manifest_and_exits_nonzero(self):
        with tempfile.TemporaryDirectory() as directory, \
                patch.object(backup, "load_config", return_value=("offline-placeholder", backup.API_BASE_DEFAULT)), \
                patch.object(backup, "api_get", return_value=None), \
                patch.object(backup, "backup_funnel") as resource_backup, \
                patch("sys.argv", ["backup_funnels.py", "--output", directory]), \
                patch("sys.stdout", new=io.StringIO()) as output:
            self.assertEqual(backup.main(), 1)
            manifest = json.loads((Path(directory) / "_backup_manifest.json").read_text())
            self.assertEqual(manifest["status"], "incomplete")
            self.assertFalse(manifest["list_complete"])
            self.assertIsNone(manifest["expected_total"])
            self.assertEqual(manifest["errors"], 1)
            self.assertNotIn("✅ バックアップ完了", output.getvalue())
            resource_backup.assert_not_called()

    def test_main_resource_failure_is_incomplete(self):
        with tempfile.TemporaryDirectory() as directory, \
                patch.object(backup, "load_config", return_value=("offline-placeholder", backup.API_BASE_DEFAULT)), \
                patch.object(backup, "api_get", return_value=listing_page(1, 1, [{"id": "sample-1", "name": "Sample"}])), \
                patch.object(backup, "backup_funnel", return_value={"steps": 0, "pages": 0, "errors": 1}), \
                patch("sys.argv", ["backup_funnels.py", "--output", directory]), \
                patch("sys.stdout", new=io.StringIO()) as output:
            self.assertEqual(backup.main(), 1)
            manifest = json.loads((Path(directory) / "_backup_manifest.json").read_text())
            self.assertEqual(manifest["status"], "incomplete")
            self.assertTrue(manifest["list_complete"])
            self.assertEqual(manifest["failure"], "resource_fetch_failed")
            self.assertIn("status: incomplete", (Path(directory) / "_backup_summary.md").read_text())
            self.assertNotIn("✅ バックアップ完了", output.getvalue())

    def test_main_verified_empty_list_returns_success(self):
        with tempfile.TemporaryDirectory() as directory, \
                patch.object(backup, "load_config", return_value=("offline-placeholder", backup.API_BASE_DEFAULT)), \
                patch.object(backup, "api_get", return_value=listing_page(1, 0, [])), \
                patch("sys.argv", ["backup_funnels.py", "--output", directory]), \
                patch("sys.stdout", new=io.StringIO()):
            self.assertEqual(backup.main(), 0)
            manifest = json.loads((Path(directory) / "_backup_manifest.json").read_text())
            self.assertEqual(manifest["status"], "complete")
            self.assertTrue(manifest["list_complete"])
            self.assertEqual(manifest["expected_total"], 0)
            self.assertEqual(manifest["errors"], 0)

    def test_failed_page_list_is_counted_as_error(self):
        with tempfile.TemporaryDirectory() as directory, \
                patch.object(backup, "api_get", side_effect=[{"data": [{"id": "step-1", "name": "Sample step"}]}, None]), \
                patch.object(backup.time, "sleep"), \
                patch("sys.stdout", new=io.StringIO()):
            result = backup.backup_funnel({"id": "funnel-1", "name": "Sample"}, Path(directory),
                                          "offline-placeholder", backup.API_BASE_DEFAULT, "synthetic-time")
            self.assertEqual(result["errors"], 1)
            self.assertEqual(result["pages"], 0)
            meta = Path(directory) / "funnels" / "Sample" / "Sample step" / "_meta.md"
            self.assertIn("status: incomplete", meta.read_text())

    def test_step_list_unknown_pagination_or_duplicates_are_incomplete(self):
        cases = (
            {"data": [], "meta": {"current_page": 1, "per_page": 20, "total": 1}},
            {"data": [], "meta": {}},
            {"data": [], "links": {"next": "https://example.invalid/next"}},
            {"data": [], "has_more": True},
            {"data": [{"id": "step-1"}, {"id": "step-1"}]},
        )
        for response in cases:
            with self.subTest(response=response), tempfile.TemporaryDirectory() as directory, \
                    patch.object(backup, "api_get", return_value=response) as transport, \
                    patch.object(backup.time, "sleep"), patch("sys.stdout", new=io.StringIO()):
                result = backup.backup_funnel({"id": "funnel-1", "name": "Sample"}, Path(directory),
                                              "offline-placeholder", backup.API_BASE_DEFAULT, "synthetic-time")
            self.assertEqual(result["errors"], 1)
            transport.assert_called_once()

    def test_page_list_unknown_pagination_or_duplicates_are_incomplete(self):
        cases = (
            {"data": [], "meta": {"current_page": 1, "per_page": 20, "total": 1}},
            {"data": [], "meta": {}},
            {"data": [], "links": {"next": "https://example.invalid/next"}},
            {"data": [], "has_more": True},
            {"data": [{"id": "page-1"}, {"id": "page-1"}]},
        )
        for response in cases:
            with self.subTest(response=response), tempfile.TemporaryDirectory() as directory, \
                    patch.object(backup, "api_get", side_effect=[{"data": [{"id": "step-1", "name": "Sample step"}]}, response]), \
                    patch.object(backup, "backup_page") as page_backup, \
                    patch.object(backup.time, "sleep"), patch("sys.stdout", new=io.StringIO()):
                result = backup.backup_funnel({"id": "funnel-1", "name": "Sample"}, Path(directory),
                                              "offline-placeholder", backup.API_BASE_DEFAULT, "synthetic-time")
                meta = Path(directory) / "funnels" / "Sample" / "Sample step" / "_meta.md"
                self.assertIn("status: incomplete", meta.read_text())
            self.assertEqual(result["errors"], 1)
            page_backup.assert_not_called()

    def test_documented_empty_steps_and_pages_remain_valid(self):
        for responses in ([{"data": []}], [{"data": [{"id": "step-1", "name": "Sample step"}]}, {"data": []}]):
            with self.subTest(responses=responses), tempfile.TemporaryDirectory() as directory, \
                    patch.object(backup, "api_get", side_effect=responses), \
                    patch.object(backup.time, "sleep"), patch("sys.stdout", new=io.StringIO()):
                result = backup.backup_funnel({"id": "funnel-1", "name": "Sample"}, Path(directory),
                                              "offline-placeholder", backup.API_BASE_DEFAULT, "synthetic-time")
            self.assertEqual(result["errors"], 0)


class BackupErrorPrivacyTests(unittest.TestCase):
    def test_http_error_logs_only_status_and_allowlisted_code(self):
        for status, code in ((401, "unauthorized"), (403, "forbidden"), (404, "not_found"),
                             (422, "validation_error"), (429, "rate_limit_exceeded"), (500, "internal_error")):
            body = json.dumps({"error": {"code": code, "message": "private-value",
                                          "details": {"mail": "private@example.invalid"}}}).encode()
            error = HTTPError("https://example.invalid/private-path", status, "private-reason", {}, io.BytesIO(body))
            with self.subTest(status=status), patch.object(backup, "MAX_RETRIES", 0), \
                    patch.object(backup, "urlopen", side_effect=error), \
                    patch("sys.stdout", new=io.StringIO()) as output:
                self.assertIsNone(backup.api_get("/private-path", "offline-placeholder", backup.API_BASE_DEFAULT))
                self.assertIn(f"status={status} code={code}", output.getvalue())
                self.assertNotIn("private", output.getvalue())
                self.assertNotIn("offline-placeholder", output.getvalue())

    def test_unrecognized_error_code_and_transport_details_are_not_logged(self):
        error = HTTPError("https://example.invalid", 401, "private", {},
                          io.BytesIO(b'{"error":{"code":"private-credential"}}'))
        for exception, expected in ((error, "unknown_error"), (URLError("private-credential"), "transport_error"),
                                    (ValueError("private-credential"), "invalid_response")):
            with self.subTest(exception=type(exception).__name__), patch.object(backup, "MAX_RETRIES", 0), \
                    patch.object(backup, "urlopen", side_effect=exception), \
                    patch("sys.stdout", new=io.StringIO()) as output:
                self.assertIsNone(backup.api_get("/funnels", "offline-placeholder", backup.API_BASE_DEFAULT))
                self.assertIn(expected, output.getvalue())
                self.assertNotIn("private-credential", output.getvalue())


if __name__ == "__main__":
    unittest.main()
