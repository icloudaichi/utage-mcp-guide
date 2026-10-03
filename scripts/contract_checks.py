"""Offline safety contracts for small UTAGE MCP read probes.

This module performs no networking. A passing local test is not evidence that a
server endpoint or its complete input schema was tested. Payloads returned by
``unwrap_result`` are transient private data; persist only ``make_receipt`` or
``types_only_projection`` outputs, never payloads or exception messages from a
transport. HTTP POST alone does not establish a tool's read/write semantics.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Mapping, Sequence


READ_TOOL_ALLOWLIST = frozenset({
    "find_tools", "message_account_list", "element_types_funnel",
    "message_reader_list", "payment_product_list",
})
PROFILE_WIRE_NAMES = {
    "lbs": "lbs", "wasa": "wasamagazine",
    "hirahara": "hirahara-daichi", "daichi": "daichi",
}
# Only these literal schema names may survive public projection. Unknown keys
# (including keys that themselves contain personal data) are never copied.
PUBLIC_FIELD_NAMES = frozenset({
    "id", "name", "title", "email", "mail", "phone", "status", "type",
    "created_at", "submitted_at", "updated_at", "total", "per_page",
    "current_page", "last_page", "data", "items", "meta", "pagination",
    "tools", "inputSchema", "properties", "required", "annotations",
    "readOnlyHint", "destructiveHint", "category", "description", "result",
    "success", "message", "account_id", "scenario_id", "product_id",
    "price", "currency", "contract_id", "next_payment_at", "payment_status",
})


class ContractError(ValueError):
    """A safe, fixed marker; never include an input value in the message."""

    def __init__(self, marker: str):
        self.marker = marker
        super().__init__(marker)


@dataclass(frozen=True)
class ReadPlan:
    tool: str
    profile_alias: str
    wire_profile: str
    arguments: Mapping[str, Any] = field(repr=False)
    schema_verified: bool = False


@dataclass(frozen=True)
class CheckedResult:
    success: bool
    marker: str | None
    http_status: int | None
    payload: Any = field(default=None, repr=False)
    identity_binding: str = "transport"


@dataclass(frozen=True)
class PaginationResult:
    complete: bool
    total: int
    per_page: int
    page_count: int
    item_count: int


def _integer(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def build_read_plan(
    tool: str, profile_alias: str, arguments: Mapping[str, Any] | None = None,
    *, descriptor: Mapping[str, Any] | None = None,
) -> ReadPlan:
    """Allow only named representative reads, never guessed/write tools.

    ``schema_verified`` remains false: this module does not implement full JSON
    Schema validation, even if a descriptor contains inputSchema. Missing or
    partial descriptors remain unverified. Conflicting semantics fail closed.
    """
    if tool not in READ_TOOL_ALLOWLIST:
        raise ContractError("tool_not_allowlisted")
    if profile_alias not in PROFILE_WIRE_NAMES:
        raise ContractError("unknown_profile")
    if arguments is not None and not isinstance(arguments, Mapping):
        raise ContractError("invalid_arguments")
    args = dict(arguments or {})
    # Sample bounds do not invent server argument names. Apply them only when a
    # caller already supplies the corresponding discovered schema field.
    for key in ("limit", "per_page"):
        if key in args and (not _integer(args[key]) or not 1 <= args[key] <= 3):
            raise ContractError("sample_limit_exceeded")
    for key in ("page", "current_page"):
        if key in args and (not _integer(args[key]) or args[key] != 1):
            raise ContractError("sample_page_exceeded")
    if any(key in args for key in ("profile", "profile_alias", "tool", "tool_name")):
        raise ContractError("argument_identity_override")
    schema_verified = False
    if descriptor is not None:
        if not isinstance(descriptor, Mapping):
            raise ContractError("invalid_descriptor")
        if descriptor.get("name", tool) != tool:
            raise ContractError("descriptor_tool_mismatch")
        annotations = descriptor.get("annotations", {})
        if not isinstance(annotations, Mapping):
            raise ContractError("invalid_descriptor")
        if any(key in annotations and not isinstance(annotations[key], bool)
               for key in ("readOnlyHint", "destructiveHint")):
            raise ContractError("invalid_descriptor")
        if (annotations.get("readOnlyHint") is False
                or annotations.get("destructiveHint") is True):
            raise ContractError("descriptor_not_read")
        # Schema presence is not schema/argument verification.
    return ReadPlan(tool, profile_alias, PROFILE_WIRE_NAMES[profile_alias], args,
                    schema_verified=schema_verified)


def execute_read_plan(
    plan: ReadPlan, transport: Callable[[ReadPlan], Any],
) -> CheckedResult:
    """Invoke an injected transport only after rechecking the immutable identity.

    The transport must bind this call to plan.wire_profile. No credential lookup,
    authentication, or HTTP transport is supplied here. Write tests use mocks.
    """
    checked = build_read_plan(plan.tool, plan.profile_alias, plan.arguments)
    if plan.wire_profile != checked.wire_profile:
        raise ContractError("plan_profile_mismatch")
    return unwrap_result(transport(checked), expected_tool=checked.tool,
                         expected_profile=checked.wire_profile)


def _auth_marker(value: Any) -> bool:
    # Examine privately, return only a fixed marker, never the original text.
    try:
        text = json.dumps(value, ensure_ascii=False).lower()
    except (TypeError, ValueError):
        return False
    return any(word in text for word in (
        "unauthorized", "unauthenticated", "auth_error", "autherror",
        "authentication", "invalid token", "token expired", "expired token",
        "invalid_api_key", "invalid api key", "permission denied", "forbidden",
        "認証", "権限がありません",
    ))


def _error_marker(value: Any, depth: int = 0) -> str | None:
    if depth > 64:
        return "invalid_result"
    if isinstance(value, Mapping):
        if value.get("type") == "text" and "text" in value:
            decoded = _decode(value["text"])
            if isinstance(decoded, (Mapping, list)):
                marker = _error_marker(decoded, depth + 1)
                if marker:
                    return marker
            elif _auth_marker(value["text"]):
                return "blocked_auth"
            elif (isinstance(value["text"], str)
                  and re.search(r"\b(error|failed|failure|exception)\b|エラー|失敗",
                                value["text"], re.IGNORECASE)):
                return "tool_error"
        if "isError" in value:
            if not isinstance(value["isError"], bool):
                return "invalid_result"
            if value["isError"]:
                return "blocked_auth" if _auth_marker(value) else "tool_error"
        for key in ("error", "errors", "exception", "fault"):
            if value.get(key):
                return "blocked_auth" if _auth_marker(value[key]) else "tool_error"
        if value.get("success") is False:
            return "blocked_auth" if _auth_marker(value) else "tool_error"
        if str(value.get("status", "")).lower() in {
            "error", "failed", "failure", "auth_error", "autherror", "unauthorized",
        }:
            return "blocked_auth" if _auth_marker(value) else "tool_error"
        if "proxy_status" in value:
            proxy_status = value["proxy_status"]
            if proxy_status not in ("ok", "success", "succeeded", 200):
                return "blocked_auth" if (proxy_status in (401, 403)
                                          or _auth_marker(value)) else "proxy_error"
        for key, child in value.items():
            # Schema property names are data, not a reported execution error.
            if key in ("inputSchema", "outputSchema", "properties"):
                continue
            marker = _error_marker(child, depth + 1)
            if marker:
                return marker
    elif isinstance(value, (list, tuple)):
        for child in value:
            marker = _error_marker(child, depth + 1)
            if marker:
                return marker
    return None


def _decode(value: Any, depth: int = 0) -> Any:
    if depth > 64:
        return None
    if isinstance(value, str):
        try:
            decoded = json.loads(value)
            return _decode(decoded, depth + 1) if isinstance(decoded, list) else decoded
        except (ValueError, TypeError):
            return None
    if isinstance(value, list) and any(
        isinstance(block, Mapping) and block.get("type") == "text" and "text" in block
        for block in value
    ):
        if len(value) != 1:
            return None
        return _decode(value[0]["text"], depth + 1)
    return value


def unwrap_result(
    response: Any, *, expected_tool: str, expected_profile: str,
) -> CheckedResult:
    """Check MCP, JSON-RPC and proxy envelopes before exposing transient payload.

    Absent identity fields are bound only by the caller's profile-bound transport;
    this is not a claim that a server echoed its identity. Any echoed mismatch is
    rejected. JSON validity or a successful outer proxy never overrides a nested
    error. Non-JSON text is not sufficient success evidence.
    """
    if expected_tool not in READ_TOOL_ALLOWLIST:
        raise ContractError("tool_not_allowlisted")
    if expected_profile not in PROFILE_WIRE_NAMES.values():
        raise ContractError("unknown_profile")
    if isinstance(response, str) and _decode(response) is None:
        return CheckedResult(False, "blocked_auth" if _auth_marker(response)
                             else "invalid_result", None)
    root = _decode(response)
    if not isinstance(root, Mapping):
        return CheckedResult(False, _error_marker(response) or "invalid_result", None)
    candidates = [root]
    text_payloads = []
    if "content" in root:
        if not isinstance(root["content"], list):
            return CheckedResult(False, "invalid_result", None)
        for block in root["content"]:
            if isinstance(block, Mapping) and block.get("type") == "text":
                decoded = _decode(block.get("text"))
                if decoded is None:
                    if _auth_marker(block.get("text")):
                        return CheckedResult(False, "blocked_auth", None)
                    if (isinstance(block.get("text"), str)
                            and re.search(r"\b(error|failed|failure|exception)\b|エラー|失敗",
                                          block["text"], re.IGNORECASE)):
                        return CheckedResult(False, "tool_error", None)
                else:
                    candidates.append(decoded)
                    text_payloads.append(decoded)
    if "structuredContent" in root:
        candidates.append(root["structuredContent"])
    http_status = None
    identity_seen = False
    inspected_envelopes = []
    expected_alias = next(alias for alias, wire in PROFILE_WIRE_NAMES.items()
                          if wire == expected_profile)
    # Inspect every wrapper branch, not individual descriptors/data array items.
    for candidate in candidates:
        pending = [(candidate, 0)]
        while pending:
            cursor, depth = pending.pop()
            if depth > 64:
                return CheckedResult(False, "invalid_result", http_status)
            if not isinstance(cursor, Mapping):
                continue
            inspected_envelopes.append(cursor)
            for key in ("http_status", "status_code"):
                if key in cursor:
                    code = cursor[key]
                    if not _integer(code) or not 100 <= code <= 599:
                        return CheckedResult(False, "invalid_http_status", None)
                    if http_status is not None and code != http_status:
                        return CheckedResult(False, "http_status_mismatch", None)
                    http_status = code
            for key in ("tool", "tool_name"):
                if key in cursor:
                    identity_seen = True
                    if cursor[key] != expected_tool:
                        return CheckedResult(False, "tool_mismatch", http_status)
            for key, expected in (("profile", expected_profile),
                                  ("profile_alias", expected_alias)):
                if key in cursor:
                    identity_seen = True
                    if cursor[key] != expected:
                        return CheckedResult(False, "profile_mismatch", http_status)
            if "jsonrpc" in cursor and "result" not in cursor and not cursor.get("error"):
                return CheckedResult(False, "invalid_result", http_status)
            for nested_key in ("structuredContent", "result", "body", "data"):
                if nested_key in cursor:
                    decoded = _decode(cursor[nested_key])
                    if not isinstance(decoded, (Mapping, list)):
                        return CheckedResult(False, "invalid_result", http_status)
                    inspected_envelopes.append(decoded)
                    pending.append((decoded, depth + 1))
    for candidate in candidates + inspected_envelopes:
        marker = _error_marker(candidate)
        if marker:
            return CheckedResult(False, marker, http_status)
    if http_status is not None and not 200 <= http_status <= 299:
        return CheckedResult(False, "blocked_auth" if http_status in (401, 403)
                             else "http_error", http_status)
    if "structuredContent" in root:
        payload = root["structuredContent"]
    elif "content" in root:
        if len(text_payloads) != 1:
            return CheckedResult(False, "invalid_result", http_status)
        payload = text_payloads[0]
    else:
        payload = root
    for _ in range(65):
        payload = _decode(payload)
        if not isinstance(payload, Mapping):
            break
        nested_key = next((key for key in ("result", "body", "data") if key in payload), None)
        if nested_key is None:
            break
        payload = payload[nested_key]
    else:
        return CheckedResult(False, "invalid_result", http_status)
    signal_fields = {
        "status", "success", "error", "errors", "message", "isError", "proxy_status",
        "tool", "tool_name", "profile", "profile_alias", "http_status", "status_code",
        "jsonrpc", "total", "per_page", "current_page", "last_page",
    }
    if (not isinstance(payload, (Mapping, list))
            or isinstance(payload, Mapping) and not set(payload).difference(signal_fields)):
        return CheckedResult(False, "invalid_result", http_status)
    # Inspect the decoded final body too (a proxy body may be a JSON string).
    marker = _error_marker(payload)
    if marker:
        return CheckedResult(False, marker, http_status)
    return CheckedResult(True, None, http_status, payload,
                         "echoed" if identity_seen else "transport")


def make_receipt(
    plan: ReadPlan, result: CheckedResult, *, item_field_names: Sequence[str] = (),
    verification_kind: str = "mock_contract",
) -> dict[str, Any]:
    """Construct a public receipt exclusively from fixed, allowlisted fields."""
    checked = build_read_plan(plan.tool, plan.profile_alias, plan.arguments)
    if plan.wire_profile != checked.wire_profile:
        raise ContractError("plan_profile_mismatch")
    if verification_kind not in ("mock_contract", "live_read"):
        raise ContractError("invalid_verification_kind")
    safe_markers = {
        None, "blocked_auth", "tool_error", "proxy_error", "invalid_result",
        "invalid_http_status", "http_status_mismatch", "tool_mismatch",
        "profile_mismatch", "http_error",
    }
    if result.marker not in safe_markers:
        raise ContractError("invalid_result_marker")
    if not isinstance(result.success, bool) or result.success != (result.marker is None):
        raise ContractError("inconsistent_result")
    if (result.http_status is not None
            and (not _integer(result.http_status) or not 100 <= result.http_status <= 599)):
        raise ContractError("invalid_http_status")
    return {
        "tool": checked.tool,
        "profile_alias": checked.profile_alias,
        "status": "success" if result.success else (
            "blocked_auth" if result.marker == "blocked_auth" else "failed"),
        "http_status": result.http_status,
        "item_field_names": sorted({name for name in item_field_names
                                    if isinstance(name, str) and name in PUBLIC_FIELD_NAMES}),
        "error_marker": result.marker,
        "schema_verified": False,
        "verification_kind": verification_kind,
    }


def types_only_projection(value: Any, _depth: int = 0) -> Any:
    """Drop every scalar value and dynamic key, retaining anonymous shape only."""
    if _depth > 64:
        raise ContractError("projection_depth_exceeded")
    if isinstance(value, Mapping):
        known = {}
        unknown = []
        for key, child in value.items():
            projected = types_only_projection(child, _depth + 1)
            if isinstance(key, str) and key in PUBLIC_FIELD_NAMES:
                known[key] = projected
            else:
                unknown.append(projected)
        return {"type": "object", "fields": known,
                "unknown_field_count": len(unknown),
                "unknown_value_shapes": _distinct_shapes(unknown)}
    if isinstance(value, (list, tuple)):
        shapes = [types_only_projection(child, _depth + 1) for child in value]
        return {"type": "array", "length": len(value),
                "item_shapes": _distinct_shapes(shapes)}
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, str):
        return "string"
    if _integer(value):
        return "integer"
    if isinstance(value, float):
        return "number"
    return "unsupported"


def _distinct_shapes(shapes: Sequence[Any]) -> list[Any]:
    unique = {json.dumps(shape, sort_keys=True): shape for shape in shapes}
    return [unique[key] for key in sorted(unique)]


def validate_pagination(
    pages: Sequence[Mapping[str, Any]], *, items_key: str = "data",
    id_key: str = "id", require_complete: bool = False,
) -> PaginationResult:
    """Verify known pages; a contiguous prefix is partial, never complete.

    Metadata may be top-level or under ``meta``/``pagination``. IDs are compared
    privately and never returned. Use require_complete=True for an all-page claim.
    """
    if not pages:
        raise ContractError("missing_page")
    seen_pages = set()
    seen_ids = set()
    total = per_page = None
    for page in pages:
        if not isinstance(page, Mapping):
            raise ContractError("invalid_page")
        metadata = page
        if not all(key in metadata for key in ("total", "per_page", "current_page")):
            metadata = page.get("meta", page.get("pagination", {}))
        if not isinstance(metadata, Mapping):
            raise ContractError("invalid_pagination_metadata")
        values = [metadata.get(key) for key in ("total", "per_page", "current_page")]
        if not all(_integer(value) for value in values):
            raise ContractError("invalid_pagination_metadata")
        page_total, page_size, number = values
        if page_total < 0 or page_size < 1 or number < 1:
            raise ContractError("invalid_pagination_metadata")
        if total is not None and page_total != total:
            raise ContractError("total_changed")
        if per_page is not None and page_size != per_page:
            raise ContractError("per_page_changed")
        total, per_page = page_total, page_size
        last_page = max(1, (total + per_page - 1) // per_page)
        if number > last_page:
            raise ContractError("page_out_of_range")
        if number in seen_pages:
            raise ContractError("duplicate_page")
        seen_pages.add(number)
        items = page.get(items_key)
        if not isinstance(items, list):
            raise ContractError("invalid_page_items")
        expected_count = min(per_page, max(0, total - (number - 1) * per_page))
        if not items and expected_count:
            raise ContractError("empty_truncation")
        if len(items) != expected_count:
            raise ContractError("page_item_count_mismatch")
        for item in items:
            if not isinstance(item, Mapping):
                raise ContractError("missing_item_id")
            item_id = item.get(id_key)
            if (not isinstance(item_id, (str, int)) or isinstance(item_id, bool)
                    or str(item_id) == ""):
                raise ContractError("missing_item_id")
            identity = str(item_id)
            if identity in seen_ids:
                raise ContractError("duplicate_item_id")
            seen_ids.add(identity)
    if sorted(seen_pages) != list(range(1, len(seen_pages) + 1)):
        raise ContractError("missing_page")
    complete = len(seen_pages) == last_page and len(seen_ids) == total
    if require_complete and not complete:
        raise ContractError("missing_page")
    return PaginationResult(complete, total, per_page, len(seen_pages), len(seen_ids))


def classify_timestamp_fields(record: Mapping[str, Any]) -> dict[str, str]:
    """Classify created_at/submitted_at separately; never assume or convert JST."""
    output = {}
    for key in ("created_at", "submitted_at"):
        if key not in record:
            output[key] = "missing"
            continue
        value = record[key]
        if value is None:
            output[key] = "null"
            continue
        if not isinstance(value, str) or "T" not in value and " " not in value:
            output[key] = "invalid"
            continue
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            output[key] = ("offset_present" if parsed.utcoffset() is not None
                           else "offset_unconfirmed")
        except ValueError:
            output[key] = "invalid"
    return output
