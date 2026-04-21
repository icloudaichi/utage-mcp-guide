#!/usr/bin/env python3
"""
report_discussion.py
GitHub Discussions に UTAGE AI Skill のフィードバックを投稿します。

使い方:
  python3 report/report_discussion.py --title "タイトル" --body "内容" [--category Bug]
"""

import argparse
import json
import os
import urllib.request
import urllib.error
from datetime import datetime

REPO_OWNER = "icloudaichi"
REPO_NAME = "utage-mcp-guide"
REPO_ID = "R_kgDOSISvZg"
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")

CATEGORIES = {
    "Bug": "DIC_kwDOSISvZs4C7VAU",       # General（バグ報告はGeneralに集約）
    "Ideas": "DIC_kwDOSISvZs4C7VAW",     # Ideas
    "General": "DIC_kwDOSISvZs4C7VAU",   # General
    "Q&A": "DIC_kwDOSISvZs4C7VAV",       # Q&A
}

BODY_TEMPLATE = """{body}

---
*このディスカッションは `report_discussion.py` によって自動投稿されました。*
*投稿日時: {date}*
*utage-mcp-guide バージョン: 0.1.0*
"""


def get_repo_id():
    """GitHub GraphQL API でリポジトリIDを取得"""
    query = """
    query {
      repository(owner: "%s", name: "%s") {
        id
        discussionCategories(first: 10) {
          nodes { id name }
        }
      }
    }
    """ % (REPO_OWNER, REPO_NAME)
    return graphql_request(query)


def create_discussion(repo_id, category_id, title, body):
    """GitHub GraphQL API でDiscussionを作成"""
    mutation = """
    mutation {
      createDiscussion(input: {
        repositoryId: "%s",
        categoryId: "%s",
        title: "%s",
        body: "%s"
      }) {
        discussion { url }
      }
    }
    """ % (repo_id, category_id, title.replace('"', '\\"'), body.replace('"', '\\"').replace('\n', '\\n'))
    return graphql_request(mutation)


def graphql_request(query):
    if not GITHUB_TOKEN:
        raise ValueError("GITHUB_TOKEN が設定されていません。.env を確認してください。")
    payload = json.dumps({"query": query}).encode()
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=payload,
        headers={
            "Authorization": f"Bearer {GITHUB_TOKEN}",
            "Content-Type": "application/json",
        }
    )
    with urllib.request.urlopen(req) as res:
        return json.loads(res.read())


def main():
    parser = argparse.ArgumentParser(description="GitHub Discussions に UTAGE AI Skill のフィードバックを投稿")
    parser.add_argument("--title", required=True, help="ディスカッションのタイトル")
    parser.add_argument("--body", required=True, help="ディスカッションの本文")
    parser.add_argument("--category", default="General", choices=["Bug", "Ideas", "General"], help="カテゴリ")
    args = parser.parse_args()

    print(f"📋 投稿内容:")
    print(f"  タイトル: {args.title}")
    print(f"  カテゴリ: {args.category}")
    print()

    # リポジトリ情報取得
    print("🔍 リポジトリ情報を取得中...")
    repo_data = get_repo_id()

    if "errors" in repo_data:
        print(f"❌ エラー: {repo_data['errors']}")
        return

    repo_id = repo_data["data"]["repository"]["id"]
    categories = {c["name"]: c["id"] for c in repo_data["data"]["repository"]["discussionCategories"]["nodes"]}

    if args.category not in categories:
        available = list(categories.keys())
        print(f"⚠️  カテゴリ '{args.category}' が見つかりません。利用可能: {available}")
        category_id = list(categories.values())[0]
    else:
        category_id = categories[args.category]

    # Discussion作成
    body = BODY_TEMPLATE.format(body=args.body, date=datetime.now().strftime("%Y-%m-%d %H:%M"))
    print("📨 投稿中...")
    result = create_discussion(repo_id, category_id, args.title, body)

    if "errors" in result:
        print(f"❌ 投稿失敗: {result['errors']}")
    else:
        url = result["data"]["createDiscussion"]["discussion"]["url"]
        print(f"✅ 投稿完了: {url}")


if __name__ == "__main__":
    main()
