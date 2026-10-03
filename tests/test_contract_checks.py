"""Offline mock contracts, not UTAGE server endpoint verification."""

import json
import unittest
from dataclasses import replace
from unittest.mock import Mock

from scripts.contract_checks import (
    CheckedResult, ContractError, ReadPlan, READ_TOOL_ALLOWLIST,
    build_read_plan, classify_timestamp_fields, execute_read_plan, make_receipt,
    types_only_projection, unwrap_result, validate_pagination,
)


class ReadGuardTests(unittest.TestCase):
    def test_allowlist_is_explicit_and_profile_bound(self):
        self.assertEqual(READ_TOOL_ALLOWLIST, {
            "find_tools", "message_account_list", "element_types_funnel",
            "message_reader_list", "payment_product_list",
        })
        plan = build_read_plan("find_tools", "hirahara", {"category": "member"})
        self.assertEqual(plan.wire_profile, "hirahara-daichi")
        self.assertFalse(plan.schema_verified)

    def test_write_unknown_and_descriptor_conflicts_never_invoke_transport(self):
        transport = Mock()
        for tool in ("subscriptioncancel", "payment", "memberupdate", "send",
                     "payment_subscription_cancel", "message_send", "unknown_list"):
            with self.subTest(tool=tool), self.assertRaises(ContractError):
                execute_read_plan(ReadPlan(tool, "lbs", "lbs", {}), transport)
        transport.assert_not_called()
        with self.assertRaisesRegex(ContractError, "descriptor_not_read"):
            build_read_plan("find_tools", "lbs", descriptor={
                "name": "find_tools", "annotations": {"readOnlyHint": False}})
        with self.assertRaisesRegex(ContractError, "descriptor_not_read"):
            build_read_plan("find_tools", "lbs", descriptor={
                "annotations": {"destructiveHint": True}})

    def test_post_method_does_not_establish_read_semantics(self):
        with self.assertRaisesRegex(ContractError, "tool_not_allowlisted"):
            build_read_plan("member_update", "lbs", descriptor={
                "method": "POST", "annotations": {"readOnlyHint": True}})
        plan = build_read_plan("find_tools", "lbs", descriptor={"method": "POST"})
        self.assertFalse(plan.schema_verified)

    def test_even_schema_presence_does_not_claim_complete_schema_verification(self):
        plan = build_read_plan("find_tools", "lbs", descriptor={
            "inputSchema": {"type": "object"},
            "annotations": {"readOnlyHint": True}})
        self.assertFalse(plan.schema_verified)

    def test_sample_bounds_and_identity_overrides(self):
        for args in ({"limit": 4}, {"per_page": True}, {"page": 2},
                     {"current_page": False}, {"profile": "other"}):
            with self.subTest(args=args), self.assertRaises(ContractError):
                build_read_plan("message_reader_list", "lbs", args)
        self.assertEqual(build_read_plan("message_reader_list", "lbs", {
            "limit": 1, "page": 1}).arguments, {"limit": 1, "page": 1})

    def test_unknown_and_forged_profile_fail_before_transport(self):
        transport = Mock()
        with self.assertRaisesRegex(ContractError, "unknown_profile"):
            build_read_plan("find_tools", "unexpected")
        with self.assertRaisesRegex(ContractError, "plan_profile_mismatch"):
            execute_read_plan(ReadPlan("find_tools", "lbs", "wasamagazine", {}), transport)
        transport.assert_not_called()

    def test_descriptor_name_and_boolean_annotation_types(self):
        for descriptor in ({"name": "send"}, {"annotations": []},
                           {"annotations": {"readOnlyHint": "false"}}):
            with self.subTest(descriptor=descriptor), self.assertRaises(ContractError):
                build_read_plan("find_tools", "lbs", descriptor=descriptor)

    def test_injected_transport_receives_only_revalidated_read_plan(self):
        transport = Mock(return_value={"result": {"items": []}})
        result = execute_read_plan(build_read_plan("find_tools", "wasa"), transport)
        self.assertTrue(result.success)
        self.assertEqual(transport.call_args.args[0].wire_profile, "wasamagazine")


class ResultTests(unittest.TestCase):
    def check(self, response):
        return unwrap_result(response, expected_tool="find_tools", expected_profile="lbs")

    def test_mcp_text_json_and_jsonrpc_success(self):
        for response in ({"content": [{"type": "text", "text": '{"tools": []}'}]},
                         {"jsonrpc": "2.0", "id": 1, "result": {"tools": []}}):
            with self.subTest(response=response):
                result = self.check(response)
                self.assertTrue(result.success)
                self.assertEqual(result.payload, {"tools": []})
                self.assertEqual(result.identity_binding, "transport")

    def test_jsonrpc_mcp_content_at_every_wrapper_depth_is_checked(self):
        cases = (
            ("not JSON", "invalid_result"),
            ('{"profile":"wasamagazine","data":[]}', "profile_mismatch"),
            ('{"tool":"send","data":[]}', "tool_mismatch"),
            ('{"http_status":500,"data":[]}', "http_error"),
            ('{"status":"success"}', "invalid_result"),
            ('{"success":"false","data":[{"id":"synthetic"}]}', "invalid_result"),
        )
        for text, marker in cases:
            rpc = {"jsonrpc": "2.0", "id": 1, "result": {
                "content": [{"type": "text", "text": text}]}}
            for response in (rpc, {"result": rpc}, {"structuredContent": rpc},
                             {"body": json.dumps(rpc)}):
                with self.subTest(marker=marker, response=response):
                    result = self.check(response)
                    self.assertFalse(result.success)
                    self.assertEqual(result.marker, marker)

    def test_nested_mcp_valid_data_is_payload_not_content_array(self):
        rpc = {"jsonrpc": "2.0", "id": 1, "result": {"isError": False, "content": [
            {"type": "text", "text": '{"profile":"lbs","http_status":200,"data":[{"id":"synthetic"}]}'}]}}
        result = self.check({"body": json.dumps(rpc)})
        self.assertTrue(result.success)
        self.assertEqual(result.payload, [{"id": "synthetic"}])
        self.assertEqual(result.http_status, 200)
        self.assertEqual(result.identity_binding, "echoed")

    def test_nested_mcp_ambiguous_content_is_not_hidden_by_structured_content(self):
        for content in ([], [{"type": "text", "text": "not JSON"}],
                        [{"type": "text", "text": '{"success":true}'}],
                        [{"type": "text", "text": '{"data":[]}'},
                         {"type": "text", "text": '{"data":[]}'}]):
            result = self.check({"jsonrpc": "2.0", "id": 1, "result": {
                "structuredContent": {"data": []}, "content": content}})
            self.assertFalse(result.success)
            self.assertEqual(result.marker, "invalid_result")
        self.assertFalse(self.check({"structuredContent": {"tools": []},
                                     "result": {"status": "success"}}).success)

    def test_success_wrapper_flag_requires_boolean(self):
        for value in ("false", "true", 0, 1, None, [], {}):
            for response in ({"success": value, "data": [{"id": "synthetic"}]},
                             {"result": {"success": value, "data": []}}):
                with self.subTest(response=response):
                    self.assertFalse(self.check(response).success)
                    self.assertEqual(self.check(response).marker, "invalid_result")

    def test_business_record_status_success_do_not_mean_tool_failure(self):
        records = [{"id": "synthetic", "status": "failed", "success": False},
                   {"id": "synthetic-2", "status": "error", "success": "unknown"}]
        for response in ({"success": True, "data": records},
                         {"result": {"content": [{"type": "text", "text": json.dumps({"data": records})}]}}):
            with self.subTest(response=response):
                result = self.check(response)
                self.assertTrue(result.success)
                self.assertEqual(result.payload, records)
        self.assertTrue(self.check({"data": {"id": "synthetic", "status": "failed",
                                             "success": False}}).success)

    def test_proxy_single_text_block_dict_and_json_are_unwrapped(self):
        for block_text in ({"data": [{"id": "sample"}]},
                           '{"data": [{"id": "sample"}]}'):
            for response in ([{"type": "text", "text": block_text}],
                             {"result": [{"type": "text", "text": block_text}]}):
                with self.subTest(response=response):
                    result = self.check(response)
                    self.assertTrue(result.success)
                    self.assertEqual(result.payload, [{"id": "sample"}])

    def test_proxy_text_block_errors_and_identity_are_rechecked(self):
        for text, marker in (
            ('{"error": {"code": -32602, "message": "Invalid params"}}', "tool_error"),
            ({"error": {"message": "Invalid token secret"}}, "blocked_auth"),
            ('{"profile": "wasamagazine", "data": []}', "profile_mismatch"),
            ({"tool": "send", "data": []}, "tool_mismatch"),
        ):
            for response in ([{"type": "text", "text": text}],
                             {"isError": False, "result": [{"type": "text", "text": text}]}):
                with self.subTest(marker=marker, response=response):
                    self.assertFalse(self.check(response).success)
                    self.assertEqual(self.check(response).marker, marker)

    def test_null_error_needs_actual_data_and_status_only_is_not_success(self):
        self.assertTrue(self.check({"error": None, "data": []}).success)
        for response in ({"error": None}, {"status": "success"},
                         {"result": {"success": True}}, {"data": None},
                         {"status": "success", "error": None}, {"total": 0},
                         {"result": [{"type": "text", "text": '{"status":"success"}'}]}):
            with self.subTest(response=response):
                self.assertFalse(self.check(response).success)

    def test_proxy_success_cannot_hide_nested_error(self):
        result = self.check({"proxy_status": "success", "isError": False,
                             "result": {"data": {"error": {"message": "failure"}}}})
        self.assertFalse(result.success)
        self.assertEqual(result.marker, "tool_error")

    def test_nested_string_error_cannot_be_hidden_by_structured_content(self):
        result = self.check({"structuredContent": {"tools": []},
                             "result": '{"error": {"message": "failure"}}'})
        self.assertFalse(result.success)
        self.assertEqual(result.marker, "tool_error")

    def test_jsonrpc_error_is_not_success(self):
        result = self.check({"jsonrpc": "2.0", "id": 1,
                             "error": {"code": -32601, "message": "missing tool"}})
        self.assertFalse(result.success)
        self.assertEqual(result.marker, "tool_error")

    def test_invalid_params_minus_32602_is_not_endpoint_success(self):
        # Observed wrong-key failure is a protocol error; the successful retry
        # with detail_id elsewhere does not turn this response into success or
        # establish that the complete inputSchema was captured.
        result = self.check({"jsonrpc": "2.0", "id": 1, "error": {
            "code": -32602, "message": "Invalid params: detail_id is required"}})
        self.assertFalse(result.success)
        self.assertEqual(result.marker, "tool_error")
        self.assertIsNone(result.payload)

    def test_error_property_in_tool_schema_is_not_execution_error(self):
        result = self.check({"tools": [{"name": "example", "inputSchema": {
            "type": "object", "properties": {"error": {"type": "string"}}}}]})
        self.assertTrue(result.success)

    def test_plain_text_error_is_not_hidden_by_structured_content(self):
        result = self.check({"structuredContent": {"tools": []}, "content": [
            {"type": "text", "text": "Error calling tool: operation failed"}]})
        self.assertFalse(result.success)
        self.assertEqual(result.marker, "tool_error")

    def test_auth_errors_return_only_safe_marker(self):
        secret = "private@example.invalid bearer-secret-123"
        for response in (
            {"isError": True, "content": [{"type": "text", "text": "AuthError " + secret}]},
            {"proxy_status": 401, "result": {"tools": []}},
            {"error": {"message": "Invalid token " + secret}},
            {"http_status": 403, "body": {"tools": []}},
            "Unauthenticated " + secret,
        ):
            with self.subTest(response=response):
                result = self.check(response)
                self.assertFalse(result.success)
                self.assertEqual(result.marker, "blocked_auth")
                self.assertIsNone(result.payload)
                self.assertNotIn(secret, repr(result))

    def test_proxy_failure_and_http_errors(self):
        for response, marker in (
            ({"proxy_status": "failed", "result": {"tools": []}}, "proxy_error"),
            ({"status_code": 500, "result": {"tools": []}}, "http_error"),
            ({"status_code": True, "result": {"tools": []}}, "invalid_http_status"),
            ({"http_status": 200, "result": {"status_code": 201}}, "http_status_mismatch"),
            ({"success": False, "data": []}, "tool_error"),
        ):
            with self.subTest(marker=marker):
                result = self.check(response)
                self.assertFalse(result.success)
                self.assertEqual(result.marker, marker)

    def test_profile_tool_and_public_alias_mismatches(self):
        for response, marker in (
            ({"profile": "wasamagazine", "result": {"tools": []}}, "profile_mismatch"),
            ({"profile_alias": "wasa", "result": {"tools": []}}, "profile_mismatch"),
            ({"tool": "send", "result": {"tools": []}}, "tool_mismatch"),
            ({"result": {"tool_name": "payment", "data": []}}, "tool_mismatch"),
        ):
            with self.subTest(response=response):
                self.assertEqual(self.check(response).marker, marker)

    def test_correct_echo_and_private_payload_repr(self):
        result = self.check({"tool": "find_tools", "profile": "lbs", "result": {
            "email": "private@example.invalid"}})
        self.assertTrue(result.success)
        self.assertEqual(result.identity_binding, "echoed")
        self.assertNotIn("private@example.invalid", repr(result))

    def test_invalid_or_ambiguous_mcp_payload_is_not_success(self):
        for response in ("success", [], {}, {"content": []},
                         {"content": [{"type": "text", "text": "done"}]},
                         {"jsonrpc": "2.0", "id": 1}, {"isError": "false"},
                         {"result": "not JSON"},
                         {"content": [{"type": "text", "text": '{}'},
                                      {"type": "text", "text": '{}'}]},
                         {"result": [{"type": "text", "text": '{"data":[]}'},
                                     {"type": "text", "text": '{"data":[]}'}]}):
            with self.subTest(response=response):
                self.assertFalse(self.check(response).success)


class PublicEvidenceTests(unittest.TestCase):
    def test_receipt_is_fixed_whitelist_and_no_payload_values(self):
        plan = build_read_plan("message_reader_list", "hirahara", {"limit": 1})
        private = "member@example.invalid"
        result = unwrap_result({"http_status": 200, "data": {private: {"email": private}}},
                               expected_tool=plan.tool, expected_profile=plan.wire_profile)
        receipt = make_receipt(plan, result,
                               item_field_names=["email", private, "token", "id"],
                               verification_kind="live_read")
        self.assertEqual(set(receipt), {
            "tool", "profile_alias", "status", "http_status", "item_field_names",
            "error_marker", "schema_verified", "verification_kind",
        })
        self.assertEqual(receipt["profile_alias"], "hirahara")
        self.assertEqual(receipt["item_field_names"], ["email", "id"])
        self.assertFalse(receipt["schema_verified"])
        self.assertNotIn(private, json.dumps(receipt))
        self.assertNotIn("hirahara-daichi", json.dumps(receipt))

    def test_types_only_drops_values_and_dynamic_keys_at_every_depth(self):
        private_values = ["member@example.invalid", "Bearer abcsecret", "payment_9281"]
        data = {
            private_values[0]: {"email": private_values[0], "id": private_values[2]},
            "data": [{"mail": private_values[0], "tokens": {
                private_values[1]: private_values[2]}, "status": "active"}],
            "total": 987654321,
        }
        projected = types_only_projection(data)
        serialized = json.dumps(projected)
        for value in private_values + ["tokens", "active", "987654321"]:
            self.assertNotIn(value, serialized)
        self.assertEqual(projected["unknown_field_count"], 1)
        self.assertEqual(projected["fields"]["total"], "integer")

    def test_scalar_types_preserve_boolean_distinction(self):
        for value, expected in ((None, "null"), (True, "boolean"), (1, "integer"),
                                (1.0, "number"), ("id", "string")):
            self.assertEqual(types_only_projection(value), expected)

    def test_arbitrary_error_marker_or_inconsistent_success_cannot_leak(self):
        plan = build_read_plan("find_tools", "lbs")
        with self.assertRaisesRegex(ContractError, "invalid_result_marker"):
            make_receipt(plan, CheckedResult(False, "secret@example.invalid", None))
        with self.assertRaisesRegex(ContractError, "inconsistent_result"):
            make_receipt(plan, CheckedResult(True, "tool_error", 200))

    def test_caller_created_success_http_error_cannot_be_a_live_receipt(self):
        plan = build_read_plan("find_tools", "lbs")
        for code in (401, 403, 500, 300, 199):
            with self.subTest(code=code), self.assertRaisesRegex(
                ContractError, "inconsistent_http_success"):
                make_receipt(plan, CheckedResult(True, None, code),
                             verification_kind="live_read")
        with self.assertRaisesRegex(ContractError, "result_binding_mismatch"):
            make_receipt(plan, CheckedResult(True, None, 200, {"tools": []}),
                         verification_kind="live_read")

    def test_receipt_rechecks_payload_status_and_original_plan_binding(self):
        plan = build_read_plan("find_tools", "lbs")
        valid = unwrap_result({"http_status": 200, "data": {"tools": []}},
                              expected_tool=plan.tool, expected_profile=plan.wire_profile)
        self.assertEqual(make_receipt(plan, valid)["status"], "success")
        for changes, marker in (
            ({"http_status": 401}, "inconsistent_http_success"),
            ({"checked_profile": "wasamagazine"}, "result_binding_mismatch"),
            ({"checked_tool": "message_account_list"}, "result_binding_mismatch"),
            ({"identity_binding": "guessed"}, "invalid_result_binding"),
            ({"payload": None}, "invalid_result_evidence"),
            ({"payload": {"status": "success"}}, "invalid_result_evidence"),
            ({"payload": {"content": [{"type": "text", "text": "not JSON"}]}},
             "invalid_result_evidence"),
            ({"payload": {"profile": "wasamagazine", "data": []}}, "invalid_result_evidence"),
        ):
            with self.subTest(changes=changes), self.assertRaisesRegex(ContractError, marker):
                make_receipt(plan, replace(valid, **changes), verification_kind="live_read")

    def test_receipt_success_without_http_status_still_needs_checked_data(self):
        plan = build_read_plan("find_tools", "lbs")
        result = unwrap_result({"tools": []}, expected_tool=plan.tool,
                               expected_profile=plan.wire_profile)
        self.assertEqual(make_receipt(plan, result)["status"], "success")
        self.assertIsNone(make_receipt(plan, result)["http_status"])


class PaginationTests(unittest.TestCase):
    @staticmethod
    def page(number, ids, total=5, per_page=2):
        return {"total": total, "per_page": per_page, "current_page": number,
                "data": [{"id": item_id} for item_id in ids]}

    def test_contiguous_prefix_is_partial_all_pages_are_complete(self):
        partial = validate_pagination([self.page(1, [1, 2])])
        self.assertFalse(partial.complete)
        pages = [self.page(1, [1, 2]), self.page(2, [3, 4]), self.page(3, [5])]
        result = validate_pagination(pages, require_complete=True)
        self.assertTrue(result.complete)
        self.assertEqual(result.item_count, 5)
        self.assertEqual(result.page_count, 3)
        self.assertNotIn("ids", vars(result))

    def test_missing_middle_and_missing_final_page_rejected(self):
        with self.assertRaisesRegex(ContractError, "missing_page"):
            validate_pagination([self.page(1, [1, 2]), self.page(3, [5])])
        with self.assertRaisesRegex(ContractError, "missing_page"):
            validate_pagination([self.page(1, [1, 2])], require_complete=True)
        with self.assertRaisesRegex(ContractError, "missing_page"):
            validate_pagination([])

    def test_duplicates_total_changes_and_empty_truncation_rejected(self):
        for pages, marker in (
            ([self.page(1, [1, 2]), self.page(2, [2, 3])], "duplicate_item_id"),
            ([self.page(1, [1, 2]), self.page(2, ["1", 3])], "duplicate_item_id"),
            ([self.page(1, [1, 2]), self.page(1, [3, 4])], "duplicate_page"),
            ([self.page(1, [1, 2]), self.page(2, [3, 4], total=6)], "total_changed"),
            ([self.page(1, [])], "empty_truncation"),
            ([self.page(1, [1])], "page_item_count_mismatch"),
        ):
            with self.subTest(marker=marker), self.assertRaisesRegex(ContractError, marker):
                validate_pagination(pages)

    def test_pagination_metadata_is_int_not_bool(self):
        for key in ("total", "per_page", "current_page"):
            page = self.page(1, [1, 2])
            page[key] = True
            with self.subTest(key=key), self.assertRaisesRegex(
                ContractError, "invalid_pagination_metadata"):
                validate_pagination([page])

    def test_nested_metadata_empty_total_and_out_of_order_pages(self):
        page = self.page(1, [], total=0)
        nested = {"meta": {key: page[key] for key in ("total", "per_page", "current_page")},
                  "data": []}
        self.assertTrue(validate_pagination([nested], require_complete=True).complete)
        self.assertTrue(validate_pagination([
            self.page(2, [3], total=3), self.page(1, [1, 2], total=3)]).complete)

    def test_invalid_ids_and_out_of_range_pages(self):
        for item_id in (None, True, "", {"id": "value"}):
            with self.subTest(item_id=item_id), self.assertRaisesRegex(
                ContractError, "missing_item_id"):
                validate_pagination([self.page(1, [item_id], total=1)])
        with self.assertRaisesRegex(ContractError, "page_out_of_range"):
            validate_pagination([self.page(4, [], total=5)])
        with self.assertRaisesRegex(ContractError, "per_page_changed"):
            validate_pagination([self.page(1, [1, 2]),
                                 self.page(2, [3], total=5, per_page=1)])


class TimestampTests(unittest.TestCase):
    def test_fields_are_distinct_and_naive_offsets_unconfirmed(self):
        self.assertEqual(classify_timestamp_fields({
            "created_at": "2026-10-03 12:30:00",
            "submitted_at": "2026-10-02T08:15:00+09:00",
        }), {"created_at": "offset_unconfirmed", "submitted_at": "offset_present"})

    def test_missing_invalid_null_and_utc(self):
        self.assertEqual(classify_timestamp_fields({
            "created_at": "2026-10-03T03:30:00Z"}),
            {"created_at": "offset_present", "submitted_at": "missing"})
        self.assertEqual(classify_timestamp_fields({"created_at": None,
                                                    "submitted_at": "2026-10-03"}),
                         {"created_at": "null", "submitted_at": "invalid"})


if __name__ == "__main__":
    unittest.main()
