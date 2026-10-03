"""Offline evidence consistency; these assertions do not contact UTAGE."""
import collections
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import Mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from contract_checks import build_read_plan, execute_read_plan, ContractError

class CatalogSnapshotTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = json.loads((ROOT / 'docs/evidence/tool-catalog-2026-10-03.json').read_text())
        cls.receipts = json.loads((ROOT / 'docs/evidence/read-receipts-2026-10-03.json').read_text())['receipts']

    def test_catalog_is_unique_complete_metadata_and_docs_match(self):
        tools = self.catalog['tools']
        self.assertEqual(len(tools), self.catalog['catalog_count'])
        self.assertEqual(len({r['name'] for r in tools}), len(tools))
        self.assertEqual(dict(collections.Counter(r['category'] for r in tools)), self.catalog['category_counts'])
        md = (ROOT / 'docs/tool-catalog.md').read_text()
        for r in tools:
            with self.subTest(tool=r['name']):
                self.assertEqual(md.count('| `' + r['name'] + '` |'), 1)
                self.assertEqual(r['input_schema'], 'not_captured')
                self.assertEqual(r['annotations'], 'not_captured')
                if r['rest']['path'] is None:
                    self.assertIsNone(r['rest']['method'])
                    self.assertIsNone(r['rest']['source'])

    def test_all_write_plans_are_rejected_before_mock_transport(self):
        writes = [r for r in self.catalog['tools'] if r['operation'] == 'write']
        self.assertEqual(len(writes), 133)
        transport = Mock()
        for r in writes:
            with self.subTest(tool=r['name']):
                with self.assertRaises(ContractError):
                    execute_read_plan(build_read_plan(r['name'], 'lbs'), transport)
                self.assertEqual(r['live_status'], 'not_run')
        transport.assert_not_called()

    def test_verified_rows_have_matching_read_receipt(self):
        by_case = {r['case']: r for r in self.receipts}
        for tool in self.catalog['tools']:
            if tool['live_status'] == 'read_verified':
                self.assertEqual(tool['operation'], 'read')
                self.assertTrue(tool['receipt_cases'])
                for case in tool['receipt_cases']:
                    self.assertEqual(by_case[case]['status'], 'read_verified')
                    self.assertEqual(by_case[case]['tool'], tool['name'])
        blocked = [r for r in self.receipts if r['status'] == 'unavailable_auth']
        self.assertEqual([r['profile_alias'] for r in blocked], ['hirahara'])
        self.assertTrue(all(r['completeness'] != 'complete' for r in self.receipts))

    def test_fixtures_are_only_anonymous_shape_not_response_values(self):
        tags = {'NoneType', 'str', 'int', 'float', 'bool', 'null', 'string', 'integer', 'number', 'boolean'}
        def walk(value):
            if isinstance(value, dict):
                for key, child in value.items():
                    self.assertNotIn('@', key)
                    walk(child)
            elif isinstance(value, list):
                for child in value:
                    walk(child)
            elif isinstance(value, str):
                self.assertIn(value, tags)
            else:
                self.assertIsInstance(value, int)
        for p in (ROOT / 'tests/fixtures').glob('*-shape.json'):
            fixture = json.loads(p.read_text())
            self.assertEqual(fixture['origin'], 'observed_types_only')
            walk(fixture['shape'])

if __name__ == '__main__':
    unittest.main()
