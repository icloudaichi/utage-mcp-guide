"""Offline evidence consistency; these assertions do not contact UTAGE."""
import collections
import json
import re
import sys
import unittest
from pathlib import Path
from unittest.mock import Mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from contract_checks import build_read_plan, execute_read_plan, ContractError, PUBLIC_FIELD_NAMES

SCALAR_SHAPE_TAGS = {
    'NoneType', 'str', 'int', 'float', 'bool',
    'null', 'string', 'integer', 'number', 'boolean',
}
# The aggregate emitted by build_catalog.py may describe unknown containers.
SUMMARY_TYPE_TAGS = SCALAR_SHAPE_TAGS | {'dict', 'list'}
SCHEMA_SHAPE_KEYS = PUBLIC_FIELD_NAMES | {
    'base_date', 'common_reader_id', 'scenario_fields', 'common_fields',
    'business_id', 'deny_multiple_purchases', 'has_sales_limit', 'is_archived',
    'max_sales_quantity', 'memo', 'order', 'product_group_id', 'product_detail_id',
    'payment_provider', 'charge_type', 'billing_cycle', 'amount', 'recurring_amount',
    'label', 'default', 'options', 'children', 'content', 'text', 'value',
    'isError', 'error', 'code', 'message', 'types',
}

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

    def assert_anonymous_shape(self, value):
        """Validate the two recorded fixture helper grammars, never raw leaves.

        Numbers are structural only at array.length and object.[other-fields].
        count. A field named length/count receives no numeric exemption.
        """
        if isinstance(value, str):
            self.assertIn(value, SCALAR_SHAPE_TAGS, 'non-type string in shape')
            return
        self.assertIsInstance(value, dict, 'raw scalar/list in shape')
        keys = set(value)
        if keys == {'object'}:
            fields = value['object']
            self.assertIsInstance(fields, dict)
            for key, child in fields.items():
                self.assertIsInstance(key, str)
                if key == '[other-fields]':
                    self.assertIsInstance(child, dict)
                    self.assertEqual(set(child), {'count', 'types'})
                    self.assertIs(type(child['count']), int)
                    self.assertGreaterEqual(child['count'], 0)
                    self.assertIsInstance(child['types'], list)
                    for tag in child['types']:
                        self.assertIsInstance(tag, str)
                        self.assertIn(tag, SUMMARY_TYPE_TAGS)
                    self.assertLessEqual(len(child['types']), child['count'])
                else:
                    self.assertTrue(key in SCHEMA_SHAPE_KEYS
                                    or re.fullmatch(r'free[0-9]{1,2}', key)
                                    or re.fullmatch(r'\[other-key-[0-9]+\]', key),
                                    'unknown key in anonymous shape')
                    self.assert_anonymous_shape(child)
        elif keys in ({'array', 'length'}, {'array_item_shapes'}):
            item_key = 'array' if 'array' in value else 'array_item_shapes'
            self.assertIsInstance(value[item_key], list)
            if item_key == 'array':
                self.assertIs(type(value['length']), int)
                self.assertGreaterEqual(value['length'], 0)
                self.assertGreaterEqual(value['length'], len(value[item_key]))
            for child in value[item_key]:
                self.assert_anonymous_shape(child)
        else:
            self.fail('unrecognized anonymous shape grammar')

    def test_shape_grammar_rejects_raw_amount_id_and_boolean_values(self):
        for shape in (
            {'object': {'amount': 123456, 'id': 9281}},
            {'object': {'amount': True}},
            {'object': {'id': {'array': [9281], 'length': 1}}},
            {'array': [9281], 'length': 1},
            {'array_item_shapes': [9281]},
            {'object': {'length': 9281}},
            {'object': {'count': 9281}},
            {'object': {'is_archived': False}},
            {'object': {'memo': None}},
            {'object': {'amount': {'count': 123456, 'types': ['int']}}},
            {'count': 9281, 'types': ['int']},
        ):
            with self.subTest(shape=shape), self.assertRaises(AssertionError):
                self.assert_anonymous_shape(shape)

    def test_shape_grammar_counts_require_exact_nonnegative_structural_integer(self):
        for bad_count in (True, False, -1, 1.0, '1', None):
            for shape in (
                {'array': [], 'length': bad_count},
                {'object': {'[other-fields]': {'count': bad_count, 'types': []}}},
            ):
                with self.subTest(shape=shape), self.assertRaises(AssertionError):
                    self.assert_anonymous_shape(shape)
        for shape in (
            {'object': {'id': 'int', 'amount': 'float'}},
            {'array': [], 'length': 0},
            {'array': [{'object': {'id': 'str'}}], 'length': 3},
            {'array_item_shapes': [{'object': {'amount': 'int'}}]},
            {'object': {'[other-fields]': {'count': 0, 'types': []}}},
            {'object': {'[other-fields]': {'count': 2, 'types': ['str', 'list']}}},
        ):
            with self.subTest(shape=shape):
                self.assert_anonymous_shape(shape)

    def test_shape_grammar_rejects_malformed_container_and_summary_nodes(self):
        for shape in (
            {'array': [], 'length': 0, 'id': 9281},
            {'array': ['str']},
            {'array': ['str'], 'length': 0},
            {'array_item_shapes': [], 'length': 0},
            {'object': {'[other-fields]': {'count': 1, 'types': [9281]}}},
            {'object': {'[other-fields]': {'count': 1, 'types': ['private-value']}}},
            {'object': {'[other-fields]': {'count': 1, 'types': [], 'id': 9281}}},
            {'object': {'[other-fields]': {'count': 0, 'types': ['str']}}},
        ):
            with self.subTest(shape=shape), self.assertRaises(AssertionError):
                self.assert_anonymous_shape(shape)

    def test_fixtures_are_only_anonymous_shape_not_response_values(self):
        for dynamic_key in ('Bearer synthetic-token', 'contract_synthetic_9281', '09012345678'):
            with self.subTest(dynamic_key=dynamic_key), self.assertRaises(AssertionError):
                self.assert_anonymous_shape({'object': {dynamic_key: 'str'}})
        for p in (ROOT / 'tests/fixtures').glob('*-shape.json'):
            fixture = json.loads(p.read_text())
            self.assertLessEqual(set(fixture), {'origin', 'case', 'tool', 'shape'})
            self.assertEqual(fixture['origin'], 'observed_types_only')
            self.assert_anonymous_shape(fixture['shape'])

if __name__ == '__main__':
    unittest.main()
