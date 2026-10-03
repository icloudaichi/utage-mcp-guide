#!/usr/bin/env python3
"""
UTAGE ファネル一括バックアップスクリプト

REST API を直接利用して全ファネルをMarkdown形式でバックアップします。
MCPツール経由だとコンテキスト上限に達するため、このスクリプトを使います。

前提:
  python3 backup/scripts/setup_apikey.py でAPIキーを設定済み

使い方:
  python3 backup/scripts/backup_funnels.py                  # 全ファネル
  python3 backup/scripts/backup_funnels.py --name "仕組み化"  # 名前で絞り込み
  python3 backup/scripts/backup_funnels.py --output ./my_backup  # 出力先指定
"""

import argparse
import json
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

# ─── 設定 ────────────────────────────────────────

# Official API base: https://docs.utage-system.com/api-reference/overview
API_BASE_DEFAULT = "https://api.utage-system.com/v1"
CONFIG_DIR = Path.home() / ".utage-mcp-guide"
ENV_FILE = CONFIG_DIR / ".env"
RATE_LIMIT_WAIT = 1.0  # API呼び出し間隔（秒）
MAX_RETRIES = 3
SAFE_ERROR_CODES = {
    "bad_request", "conflict", "forbidden", "internal_error", "invalid_encoding",
    "invalid_filetype", "not_found", "rate_limit_exceeded", "unauthorized",
    "validation_error", "monthly_limit_exceeded", "hourly_limit_exceeded",
    "total_limit_exceeded", "not_uploaded", "folder_not_found",
}


# ─── ユーティリティ ──────────────────────────────

def normalize_api_base(base_url: str) -> str:
    """Accept an origin or a versioned base without appending /v1 twice."""
    base_url = base_url.strip().rstrip("/")
    # Migrate the previous default if it was copied into an existing config.
    if not base_url or base_url in {
        "https://utage-system.com/api", "https://utage-system.com/api/v1"
    }:
        return API_BASE_DEFAULT
    return base_url if base_url.endswith("/v1") else f"{base_url}/v1"


def load_config() -> tuple:
    """~/.utage-mcp-guide/.env からAPIキーとベースURLを読み込む"""
    if not ENV_FILE.exists():
        print("❌ APIキーが設定されていません。")
        print("   先に以下を実行してください:")
        print("   python3 backup/scripts/setup_apikey.py")
        sys.exit(1)

    api_key = ""
    base_url = ""
    for line in ENV_FILE.read_text().splitlines():
        if line.startswith("UTAGE_API_KEY=") and not line.startswith("#"):
            api_key = line.split("=", 1)[1].strip()
        elif line.startswith("UTAGE_BASE_URL=") and not line.startswith("#"):
            base_url = line.split("=", 1)[1].strip().rstrip("/")

    if not api_key:
        print("❌ APIキーが空です。setup_apikey.py を再実行してください。")
        sys.exit(1)

    api_base = normalize_api_base(base_url)
    return api_key, api_base


def api_get(endpoint: str, api_key: str, api_base: str, params: dict = None) -> dict:
    """UTAGE REST API にGETリクエスト（429リトライ付き）"""
    url = f"{api_base}{endpoint}"
    if params:
        query = "&".join(f"{k}={v}" for k, v in params.items() if v is not None)
        url = f"{url}?{query}"

    for attempt in range(MAX_RETRIES + 1):
        req = Request(url, headers={
            "Authorization": f"Bearer {api_key}",
            "Accept": "application/json",
            "User-Agent": "UTAGE-Backup-Script/1.0",
        })

        try:
            with urlopen(req, timeout=30) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                if not isinstance(result, dict) or "error" in result:
                    print("  ⚠️  status=invalid_response code=invalid_response")
                    return None
                return result
        except HTTPError as e:
            if e.code == 429 and attempt < MAX_RETRIES:
                wait = (attempt + 1) * 5  # 5s, 10s, 15s
                print(f"  ⏳ レート制限 → {wait}秒待機 (リトライ {attempt+1}/{MAX_RETRIES})")
                time.sleep(wait)
                continue
            # Error messages/details may contain contact data or tokens. Keep only
            # the HTTP status and a known, fixed API error code in console logs.
            code = "unknown_error"
            try:
                error = json.loads(e.read(4096).decode("utf-8"))
                candidate = error.get("error", {}).get("code")
                if isinstance(candidate, str) and candidate in SAFE_ERROR_CODES:
                    code = candidate
            except Exception:
                pass
            print(f"  ⚠️  status={e.code} code={code}")
            return None
        except URLError:
            print("  ⚠️  status=transport_error code=transport_error")
            return None
        except Exception:
            if attempt < MAX_RETRIES:
                wait = (attempt + 1) * 3
                print(f"  ⏳ code=invalid_response → {wait}秒待機")
                time.sleep(wait)
                continue
            print("  ⚠️  status=invalid_response code=invalid_response")
            return None
    return None


def fetch_all_funnels(api_key: str, api_base: str) -> tuple:
    """Return a checked full list and completeness metadata, never guess totals."""
    funnels = []
    seen_ids = set()
    expected_total = None
    expected_per_page = None
    page = 1
    while True:
        resp = api_get("/funnels", api_key, api_base, {"page": page, "per_page": 100})
        if resp is None:
            failure = "api_error"
            break
        data, meta = resp.get("data"), resp.get("meta")
        if not isinstance(data, list) or not isinstance(meta, dict):
            failure = "invalid_pagination"
            break
        current_page, per_page, total = (meta.get(k) for k in ("current_page", "per_page", "total"))
        if (any(type(v) is not int for v in (current_page, per_page, total))
                or current_page != page or not 1 <= per_page <= 100 or total < 0
                or len(data) > per_page):
            failure = "invalid_pagination"
            break
        if expected_total is None:
            expected_total, expected_per_page = total, per_page
        elif total != expected_total or per_page != expected_per_page:
            failure = "pagination_changed"
            break
        expected_count = min(per_page, max(total - (page - 1) * per_page, 0))
        if len(data) != expected_count:
            failure = "count_mismatch"
            break
        if any(not isinstance(f, dict) or not isinstance(f.get("id"), str)
               or not f["id"] or not isinstance(f.get("name"), str) for f in data):
            failure = "invalid_resource"
            break
        ids = [f["id"] for f in data]
        if len(ids) != len(set(ids)) or seen_ids.intersection(ids):
            failure = "duplicate_resource"
            break
        funnels.extend(data)
        seen_ids.update(ids)
        if page * per_page >= expected_total:
            complete = len(funnels) == expected_total
            return funnels, {"complete": complete, "expected_total": expected_total,
                             "failure": None if complete else "count_mismatch"}
        if not data:
            failure = "count_mismatch"
            break
        page += 1
        time.sleep(RATE_LIMIT_WAIT)
    return funnels, {"complete": False, "expected_total": expected_total, "failure": failure}


def non_paginated_list(response: dict):
    """Check the endpoint-specific steps/pages schema; reject unknown paging."""
    # Their official specs expose only data, without page/per_page parameters:
    # https://docs.utage-system.com/api-reference/funnel/step-list
    # https://docs.utage-system.com/api-reference/funnel/page-list
    if not isinstance(response, dict) or set(response) != {"data"}:
        return None
    data = response["data"]
    if (not isinstance(data, list)
            or any(not isinstance(item, dict) or not isinstance(item.get("id"), str)
                   or not item["id"] for item in data)):
        return None
    ids = [item["id"] for item in data]
    return data if len(ids) == len(set(ids)) else None


def sanitize(name: str) -> str:
    """ファイル名に使えない文字を置換"""
    return re.sub(r'[/:*?"<>|\\]', '_', name)[:100].strip()


def write_md(path: Path, content: str):
    """Markdownファイルを書き込み"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


# ─── バックアップ処理 ────────────────────────────

def backup_page(funnel_id: str, step_id: str, page_meta: dict,
                step_dir: Path, api_key: str, api_base: str, ts: str) -> bool:
    """1ページの詳細を取得してMarkdownに保存"""
    page_id = page_meta["id"]
    title = page_meta.get("title") or f"page_{page_meta.get('order', 0)}"
    filename = sanitize(title) or f"page_{page_id}"

    time.sleep(RATE_LIMIT_WAIT)
    resp = api_get(f"/funnels/{funnel_id}/steps/{step_id}/pages/{page_id}", api_key, api_base)
    if not resp or not isinstance(resp.get("data"), dict):
        # エラー時はメタデータのみ保存
        write_md(step_dir / f"{filename}.md",
                 f"---\ntype: page\nid: \"{page_id}\"\nstatus: error\n---\n\n"
                 f"# ページ: {title}\n\n> ⚠️ API取得エラー\n")
        return False

    pdata = resp["data"]
    ct = pdata.get("content_type", "elements")

    # 要素データまたはHTMLソース
    if ct == "elements":
        body = json.dumps(pdata.get("elements", []), ensure_ascii=False, indent=2)
        body_section = f"## 要素データ\n\n```json\n{body}\n```"
    else:
        body = pdata.get("html_source", "")
        body_section = f"## HTMLソース\n\n```html\n{body}\n```"

    # CSS / JS フィールド
    extras = ""
    for field in ["css", "js_head", "js_body", "js_body_top"]:
        val = pdata.get(field)
        if val:
            extras += f"\n## {field}\n\n```\n{val}\n```\n"

    content = f"""---
type: page
id: "{pdata.get('id', page_id)}"
funnel_id: "{funnel_id}"
step_id: "{step_id}"
title: "{pdata.get('title', '')}"
content_type: "{ct}"
page_title: {json.dumps(pdata.get('page_title'), ensure_ascii=False)}
step_url: "{pdata.get('step_url', '')}"
page_url: "{pdata.get('page_url', '')}"
pc_width: {pdata.get('pc_width', 'null')}
background_color: "{pdata.get('background_color', '')}"
is_no_index: {pdata.get('is_no_index', 0)}
order: {pdata.get('order', 0)}
is_archived: {pdata.get('is_archived', 0)}
created_at: "{pdata.get('created_at', '')}"
updated_at: "{pdata.get('updated_at', '')}"
backed_up_at: "{ts}"
---

# ページ: {pdata.get('title', title)}

## ページ設定

| 項目 | 値 |
|:---|:---|
| コンテンツタイプ | {ct} |
| PC幅 | {pdata.get('pc_width', '')} |
| 背景色 | {pdata.get('background_color', '')} |
| noindex | {'はい' if pdata.get('is_no_index') else 'いいえ'} |

{body_section}
{extras}"""

    write_md(step_dir / f"{filename}.md", content)
    return True


def backup_funnel(funnel: dict, output_dir: Path, api_key: str, api_base: str, ts: str) -> dict:
    """1ファネルをバックアップ"""
    funnel_id = funnel["id"]
    funnel_name = funnel["name"]
    fn = sanitize(funnel_name) or f"funnel_{funnel_id}"
    funnel_dir = output_dir / "funnels" / fn

    print(f"\n📁 {funnel_name}")

    # ステップ一覧を取得
    time.sleep(RATE_LIMIT_WAIT)
    steps_resp = api_get(f"/funnels/{funnel_id}/steps", api_key, api_base)
    steps = non_paginated_list(steps_resp)
    if steps is None:
        print("  ⚠️  status=incomplete code=step_list_failed")
        return {"steps": 0, "pages": 0, "errors": 1}

    # ファネル _meta.md
    write_md(funnel_dir / "_meta.md", f"""---
type: funnel
id: "{funnel_id}"
name: "{funnel_name}"
created_at: "{funnel.get('created_at', '')}"
updated_at: "{funnel.get('updated_at', '')}"
backed_up_at: "{ts}"
steps_count: {len(steps)}
---

# ファネル: {funnel_name}

| 項目 | 値 |
|:---|:---|
| ID | {funnel_id} |
| 作成日 | {funnel.get('created_at', '')[:10]} |
| 更新日 | {funnel.get('updated_at', '')[:10]} |
| ステップ数 | {len(steps)} |
""")

    total_pages = 0
    total_errors = 0

    for step in steps:
        step_id = step["id"]
        step_name = step.get("name", f"step_{step_id}")
        sn = sanitize(step_name) or f"step_{step_id}"
        step_dir = funnel_dir / sn

        # ページ一覧を取得
        time.sleep(RATE_LIMIT_WAIT)
        pages_resp = api_get(f"/funnels/{funnel_id}/steps/{step_id}/pages", api_key, api_base)
        checked_pages = non_paginated_list(pages_resp)
        pages_ok = checked_pages is not None
        pages = checked_pages if pages_ok else []
        if not pages_ok:
            total_errors += 1
            print("  ⚠️  status=incomplete code=page_list_failed")

        # ステップ _meta.md
        write_md(step_dir / "_meta.md", f"""---
type: step
id: "{step_id}"
funnel_id: "{funnel_id}"
name: "{step_name}"
step_url: "{step.get('step_url', '')}"
order: {step.get('order', 0)}
backed_up_at: "{ts}"
pages_count: {len(pages)}
status: {'complete' if pages_ok else 'incomplete'}
---

# ステップ: {step_name}

| 項目 | 値 |
|:---|:---|
| ID | {step_id} |
| 公開URL | {step.get('step_url', '')} |
| 並び順 | {step.get('order', 0)} |
| ページ数 | {len(pages)} |
""")

        # 各ページの詳細を取得
        for page in pages:
            ok = backup_page(funnel_id, step_id, page, step_dir, api_key, api_base, ts)
            total_pages += 1
            if not ok:
                total_errors += 1
            p_title = page.get("title", "?")[:30]
            status = "✓" if ok else "✗"
            print(f"  {status} {step_name}/{p_title}")

    return {"steps": len(steps), "pages": total_pages, "errors": total_errors}


def main():
    parser = argparse.ArgumentParser(description="UTAGE ファネル一括バックアップ")
    parser.add_argument("--name", help="ファネル名で絞り込み（部分一致）")
    parser.add_argument("--output", help="出力先ディレクトリ", default=None)
    args = parser.parse_args()

    api_key, api_base = load_config()
    ts = datetime.now().astimezone().isoformat()
    date_str = datetime.now().strftime("%Y-%m-%d")

    output_dir = Path(args.output) if args.output else Path(f"backup_{date_str}")

    print("=" * 50)
    print("  UTAGE ファネル一括バックアップ")
    print("=" * 50)
    print(f"  API:    {api_base}")
    print(f"  出力先: {output_dir}")
    print(f"  日時:   {ts}")
    print()

    # ファネル一覧を取得
    print("📋 ファネル一覧を取得中...")
    all_funnels, listing = fetch_all_funnels(api_key, api_base)
    fetched_funnel_count = len(all_funnels)

    # 名前フィルタ
    if args.name:
        all_funnels = [f for f in all_funnels if args.name in f["name"]]

    print(f"   {len(all_funnels)} 件のファネルが見つかりました")

    # ファネルリストをJSONとして保存
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "funnel_list.json").write_text(
        json.dumps({"data": all_funnels, "meta": listing}, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    manifest_path = output_dir / "_backup_manifest.json"
    manifest = {"status": "incomplete", "list_complete": listing["complete"],
                "expected_total": listing["expected_total"],
                "fetched_funnels": fetched_funnel_count,
                "selected_funnels": len(all_funnels), "errors": 1,
                "failure": listing["failure"]}
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    if not listing["complete"]:
        print(f"  ⚠️  バックアップ不完全: code={listing['failure']}")
        return 1

    # バックアップ実行
    stats = {"funnels": 0, "steps": 0, "pages": 0, "errors": 0}

    for i, funnel in enumerate(all_funnels):
        print(f"\n[{i+1}/{len(all_funnels)}]", end="")
        result = backup_funnel(funnel, output_dir, api_key, api_base, ts)
        stats["funnels"] += 1
        stats["steps"] += result["steps"]
        stats["pages"] += result["pages"]
        stats["errors"] += result["errors"]

    manifest.update(status="complete" if stats["errors"] == 0 else "incomplete",
                    errors=stats["errors"], failure=None if stats["errors"] == 0 else "resource_fetch_failed")
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    # サマリーを作成
    summary = f"""---
type: backup_summary
status: {manifest['status']}
backed_up_at: "{ts}"
total_funnels: {stats['funnels']}
total_steps: {stats['steps']}
total_pages: {stats['pages']}
total_errors: {stats['errors']}
---

# UTAGEファネルバックアップサマリー

**実行日時:** {ts}

## 統計

| カテゴリ | 件数 |
|:---|:---|
| ファネル | {stats['funnels']} |
| ステップ | {stats['steps']} |
| ページ | {stats['pages']} |
| エラー | {stats['errors']} |

## ファネル一覧

| # | ファネル名 | 最終更新 |
|:---|:---|:---|
""" + "\n".join(
        f"| {i+1} | {f['name']} | {f.get('updated_at', '')[:10]} |"
        for i, f in enumerate(all_funnels)
    ) + "\n"

    write_md(output_dir / "_backup_summary.md", summary)

    print()
    print("=" * 50)
    print("  ✅ バックアップ完了!" if stats["errors"] == 0 else "  ⚠️  バックアップ不完全")
    print(f"  📁 {output_dir}")
    print(f"  ファネル: {stats['funnels']} / ステップ: {stats['steps']} / ページ: {stats['pages']}")
    if stats["errors"]:
        print(f"  ⚠️  エラー: {stats['errors']} 件")
    print("=" * 50)
    return 0 if stats["errors"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
