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
            meta = Path(directory) / "funnels" / backup.resource_basename("Sample", "funnel-1") / backup.resource_basename("Sample step", "step-1") / "_meta.md"
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
                meta = Path(directory) / "funnels" / backup.resource_basename("Sample", "funnel-1") / backup.resource_basename("Sample step", "step-1") / "_meta.md"
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


class BackupPageDetailTests(unittest.TestCase):
    def test_empty_detail_fails_main_without_synthesizing_body(self):
        responses = [listing_page(1, 1, [{"id": "funnel-1", "name": "Sample"}]),
                     {"data": [{"id": "step-1", "name": "Sample step"}]},
                     {"data": [{"id": "page-1", "title": "Sample page", "content_type": "elements"}]},
                     {"data": {}}]
        with tempfile.TemporaryDirectory() as directory, \
                patch.object(backup, "load_config", return_value=("offline-placeholder", backup.API_BASE_DEFAULT)), \
                patch.object(backup, "api_get", side_effect=responses), \
                patch.object(backup.time, "sleep"), \
                patch("sys.argv", ["backup_funnels.py", "--output", directory]), \
                patch("sys.stdout", new=io.StringIO()) as output:
            self.assertEqual(backup.main(), 1)
            manifest = json.loads((Path(directory) / "_backup_manifest.json").read_text())
            self.assertEqual(manifest["status"], "incomplete")
            self.assertEqual(manifest["errors"], 1)
            step_dir = Path(directory) / "funnels" / backup.resource_basename("Sample", "funnel-1") / backup.resource_basename("Sample step", "step-1")
            page = step_dir / f"{backup.resource_basename('Sample page', 'page-1')}.md"
            self.assertIn("status: error", page.read_text())
            self.assertNotIn("## 要素データ", page.read_text())
            self.assertIn("status: incomplete", (step_dir / "_meta.md").read_text())
            self.assertIn("errors: 1", (step_dir / "_meta.md").read_text())
            self.assertNotIn("✅ バックアップ完了", output.getvalue())

    def test_missing_mismatched_or_incompatible_detail_is_rejected(self):
        invalid = (
            {},
            {"content_type": "elements", "elements": []},
            {"id": "other-page", "content_type": "elements", "elements": []},
            {"id": 1, "content_type": "elements", "elements": []},
            {"id": "page-1", "elements": []},
            {"id": "page-1", "content_type": "unknown", "elements": []},
            {"id": "page-1", "content_type": [], "elements": []},
            {"id": "page-1", "content_type": "elements"},
            {"id": "page-1", "content_type": "elements", "html_source": ""},
            {"id": "page-1", "content_type": "elements", "elements": None},
            {"id": "page-1", "content_type": "elements", "elements": "[]"},
            {"id": "page-1", "content_type": "elements", "elements": [None]},
            {"id": "page-1", "content_type": "raw_html", "elements": []},
            {"id": "page-1", "content_type": "raw_html", "html_source": None},
            {"id": "page-1", "content_type": "raw_html", "html_source": []},
        )
        for data in invalid:
            with self.subTest(data=data), tempfile.TemporaryDirectory() as directory, \
                    patch.object(backup, "api_get", return_value={"data": data}), \
                    patch.object(backup.time, "sleep"), patch("sys.stdout", new=io.StringIO()):
                self.assertFalse(backup.backup_page("funnel-1", "step-1", {"id": "page-1", "title": "Sample"},
                                                   Path(directory), "offline-placeholder", backup.API_BASE_DEFAULT, "synthetic-time"))
                self.assertIn("status: error", (Path(directory) / f"{backup.resource_basename('Sample', 'page-1')}.md").read_text())

    def test_detail_type_must_match_list_metadata_when_present(self):
        with tempfile.TemporaryDirectory() as directory, \
                patch.object(backup, "api_get", return_value={"data": {"id": "page-1", "content_type": "elements", "elements": []}}), \
                patch.object(backup.time, "sleep"), patch("sys.stdout", new=io.StringIO()):
            self.assertFalse(backup.backup_page("funnel-1", "step-1", {"id": "page-1", "title": "Sample", "content_type": "raw_html"},
                                               Path(directory), "offline-placeholder", backup.API_BASE_DEFAULT, "synthetic-time"))

    def test_explicit_empty_bodies_are_valid(self):
        valid = ({"id": "page-1", "content_type": "elements", "elements": []},
                 {"id": "page-1", "content_type": "raw_html", "html_source": ""},
                 {"id": "page-1", "content_type": "elements", "elements": [], "html_source": ""})
        for data in valid:
            with self.subTest(data=data), tempfile.TemporaryDirectory() as directory, \
                    patch.object(backup, "api_get", return_value={"data": data}), \
                    patch.object(backup.time, "sleep"):
                self.assertTrue(backup.backup_page("funnel-1", "step-1", {"id": "page-1", "title": "Sample", "content_type": data["content_type"]},
                                                  Path(directory), "offline-placeholder", backup.API_BASE_DEFAULT, "synthetic-time"))
                self.assertNotIn("status: error", (Path(directory) / f"{backup.resource_basename('Sample', 'page-1')}.md").read_text())


class BackupResourceCollisionTests(unittest.TestCase):
    def test_long_multibyte_label_can_be_saved_with_digest(self):
        filename = backup.resource_basename("講座" * 80, "sample-page") + ".md"
        self.assertLessEqual(len(filename.encode("utf-8")), 255)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / filename
            backup.write_md(path, "synthetic content")
            self.assertEqual(path.read_text(), "synthetic content")

    def test_same_labels_and_lossy_id_pairs_produce_distinct_backups(self):
        # Each pair would collide if its ID were only sanitized (slash -> _ and
        # colon -> _). Use two same-name funnels, steps, and pages in every parent.
        funnel_ids = ("funnel/a", "funnel:a")
        step_ids = ("step/a", "step:a")
        page_ids = ("page/a", "page:a")
        responses = {"/funnels": listing_page(1, 2, [{"id": id_, "name": "Same"} for id_ in funnel_ids], per_page=100)}
        for funnel_id in funnel_ids:
            responses[f"/funnels/{funnel_id}/steps"] = {"data": [{"id": id_, "name": "Same"} for id_ in step_ids]}
            for step_id in step_ids:
                base = f"/funnels/{funnel_id}/steps/{step_id}/pages"
                responses[base] = {"data": [{"id": id_, "title": "Same", "content_type": "elements"} for id_ in page_ids]}
                for page_id in page_ids:
                    responses[f"{base}/{page_id}"] = {"data": {"id": page_id, "title": "Same", "content_type": "elements", "elements": []}}

        with tempfile.TemporaryDirectory() as directory, \
                patch.object(backup, "load_config", return_value=("offline-placeholder", backup.API_BASE_DEFAULT)), \
                patch.object(backup, "api_get", side_effect=lambda endpoint, *_: responses[endpoint]), \
                patch.object(backup.time, "sleep"), \
                patch("sys.argv", ["backup_funnels.py", "--output", directory]), \
                patch("sys.stdout", new=io.StringIO()):
            self.assertEqual(backup.main(), 0)
            root = Path(directory)
            manifest = json.loads((root / "_backup_manifest.json").read_text())
            self.assertEqual(manifest["status"], "complete")
            self.assertEqual(manifest["errors"], 0)
            funnel_dirs = [path for path in (root / "funnels").iterdir() if path.is_dir()]
            self.assertEqual(len(funnel_dirs), 2)
            self.assertEqual({path.joinpath("_meta.md").read_text().split('id: "')[1].split('"')[0] for path in funnel_dirs}, set(funnel_ids))
            page_files = []
            for funnel_dir in funnel_dirs:
                step_dirs = [path for path in funnel_dir.iterdir() if path.is_dir()]
                self.assertEqual(len(step_dirs), 2)
                self.assertEqual({path.joinpath("_meta.md").read_text().split('id: "')[1].split('"')[0] for path in step_dirs}, set(step_ids))
                for step_dir in step_dirs:
                    self.assertIn("status: complete", (step_dir / "_meta.md").read_text())
                    files = [path for path in step_dir.glob("*.md") if path.name != "_meta.md"]
                    self.assertEqual(len(files), 2)
                    self.assertEqual({path.read_text().split('id: "')[1].split('"')[0] for path in files}, set(page_ids))
                    page_files.extend(files)
            self.assertEqual(len(set(page_files)), 8)
            self.assertFalse(any(path.parent == root for path in page_files))


if __name__ == "__main__":
    unittest.main()
