# MAGI MELCHIOR 初回独立レビュー

- 観点: 仕組み設計、整合性、安全性
- 対象: `icloudaichi/utage-mcp-guide` の固定commit `5a65fe111afb187e28459ec78931d9a9605c5098`
- baseline: `7f05b0c0`、対象snapshot: `private/review-initial`
- 実際に全文確認した指示: `installed prompts/magi_reviewer.md`、`installed skills/magi_reviewer/SKILL.md`
- 手順: 他reviewer結果を受け取らず独立レビュー。元skillは日報向けのため、親の明示指示により独立3者・相互批判・修正後再reviewをPRレビューへ適用。個人skills/configは編集していない。
- 制限: ネットワーク、実サービス、credentialアクセスなし。repo編集なし。以下は全て公開snapshotと合成値を使ったoffline再現。

## 判定

P0は検出なし。P1 2件とP2 1件を検出。初回段階でmerge承認できない。成功判定およびbackup完全性の修正・回帰テスト後に再reviewが必要。

### ❌ P1 M1: JSON-RPC内のMCP contentを正規化せず、失敗・別profileを成功にする

- 場所: `scripts/contract_checks.py:300`–306、322–345。狭い指摘位置は300–306。
- 条件: 標準的なJSON-RPC `result` にMCP CallToolResultの`content`がある場合。
- 原因: envelope走査は`structuredContent/result/body/data`のみを辿り、最上位以外の`content`内textをdecodeしてidentity/HTTP status検査しない。最終payloadも`content`を残したMappingとなり、非signal fieldの存在だけで成功となる。
- 再現:

```python
from scripts.contract_checks import unwrap_result
import json
for text in (
    "not JSON",
    json.dumps({"profile": "wasamagazine", "data": []}),
    json.dumps({"http_status": 500, "data": []}),
    json.dumps({"success": True}),
):
    result = unwrap_result(
        {"jsonrpc": "2.0", "id": 1, "result": {
            "content": [{"type": "text", "text": text}]}},
        expected_tool="find_tools", expected_profile="lbs")
    print(result.success, result.marker, result.http_status)
# 4ケース全て: True None None
```

- 影響: 文書が明示する「非JSON/別profile/HTTP error/成功signalのみを成功扱いしない」がenvelope形により破られる。誤ったlive receiptや接続対象の誤認に繋がる。これは実サービスでこの形が観測されたと主張するものではない。
- 修正: 全wrapper depthでCallToolResultを正規化し、decoded `content`/`structuredContent`の全branchをidentity/status/error検査へ渡す。未知/非JSON/曖昧なcontentはfail closed。最終payloadからenvelope-only Mappingを除き、実payloadへ展開する。
- 回帰: 上記4ケース失敗、正しいnested JSON-RPC→MCP→text JSONは実dataへ展開、nested `structuredContent`と`content`の不一致も拒否。
- 文脈仮説A: 既存proxyはroot text-listだけを返し、当日のread証跡には影響がない。仮説B: 今後のクライアント/JSON-RPC入力はresult.contentを返し、問題が顕在化する。現行moduleはMCP/JSON-RPC一般を扱う契約なので、この不確実性は修正を省く理由にならない。

### ❌ P1 M2: 不完全/別ページの詳細を成功としてバックアップしcompleteにする

- 場所: `backup/scripts/backup_funnels.py:225`–241（新たなresponse条件の225–230が指摘位置）、`main`の440–444。
- 条件: page GETの`data`が空object、別ID、またはHTML content_typeだがbody欠落。
- 原因: `data`がdictかしか検査せず、欠落content_typeを`elements`、欠落elementsを`[]`、欠落html_sourceを`""`とする。ページid照合もない。`backup_page`がTrueを返すため`backup_funnel`のerrorsは0、新manifestはcompleteとなる。
- offline再現: `api_get`を下記応答でmockして`backup_page('f1','s1',{'id':'p1','title':'Page'},tempdir,...)`を呼ぶと、全てTrueで1ファイル生成。

```python
{"data": {}}
{"data": {"id": "wrong", "content_type": "elements", "elements": []}}
{"data": {"id": "p1", "content_type": "html"}}
```

- `backup_funnel`へsteps→pages→detailの3応答を`[{"data":[{"id":"step","name":"Step"}]},{"data":[{"id":"p1","title":"Page"}]},{"data":{}}]`として渡す再現結果: `{'steps': 1, 'pages': 1, 'errors': 0}`。
- 影響: 壊れた/別resourceのバックアップを完全と表示し、復元に必要な本文がなくても利用者が取得成功と誤認する。既存処理にdefault補完があったが、今回変更したチェックと新complete契約の穴として修正が必要。
- 修正: page detailのresource ID一致を必須検査。対応するcontent_typeと本文fieldの存在・型を検査し、未知/欠落をFalseとしてcountする。正規に空のelements/HTMLは、fieldが存在し型が正しければ許容する。未知typeをHTMLとして扱わない。
- 回帰: 空detail、missing ID、wrong ID、missing elements、missing HTML、未知typeを失敗/incomplete扱い。正規に空のbodyは成功。

### ❌ P2 M3: HTTP 401のCheckedResultからsuccess receiptを生成できる

- 場所: `scripts/contract_checks.py:365`–369。
- 再現:

```python
from scripts.contract_checks import build_read_plan, CheckedResult, make_receipt
receipt = make_receipt(build_read_plan("find_tools", "lbs"),
                       CheckedResult(True, None, 401))
# receipt['status'] == 'success'; receipt['http_status'] == 401
```

- 原因: `make_receipt`はmarker/successの一致を検査するが、successとHTTP statusの整合性を検査しない。
- 影響: `unwrap_result`経由なら通常発生しないが、public dataclassから手動構築可能で、receipt自体に矛盾した成功証跡が残る。実receiptが偽造されていたと主張するものではない。
- 修正: successならstatusがNoneまたは2xxであることを必須検査。401/403など非2xxのsuccessをContractErrorで拒否。回帰テストを追加。

## ◎ 評価できる点

- `find_tools` metadata、schema/annotations未取得、live read、mock契約の区別が文書・catalog・fixtureへ揃えて記録されている。未知スキーマの未検証を成功へ転記する危険を減らしている。
- `types_only_projection`は値だけでなく未知の動的キーも除去し、receiptは固定markerとfield allowlistに限定する。PIIがキーに混入する経路にも対処している。
- 全133writeがallowlistより拒否され、transport未呼出しをmockで確認。実サービスの変更系を0件に維持する設計が明確。
- 一覧paginationはpageごとの期待件数・total変化・重複ID・欠落page・bool型metaを確認する。空応答を全件成功へ誤認する旧挙動の改善が適切。
- 商品plan設定と個人契約/次回課金/外部subscription IDを分け、auth blockedと個別read未取得を断定的な不可能判断へ変換していない。
- setupが全認証cache削除とTLS無効化の案内を除いた点は、他接続を壊す復旧とsecret漏えいのリスクを減らす。

## 検証証跡

`PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -q` をsnapshotで実行。

```text
Ran 56 tests in 0.044s
OK
```

追加合成再現の出力:

```text
nested_plain_text       success=True marker=None http_status=None
nested_profile_mismatch success=True marker=None http_status=None
nested_http_failure      success=True marker=None http_status=None
nested_status_only       success=True marker=None http_status=None
empty_page_data          success=True output_files=1
wrong_page_id            success=True output_files=1
html_missing_body        success=True output_files=1
backup_funnel_empty_detail {'steps': 1, 'pages': 1, 'errors': 0}
receipt_conflicting_http  status=success http_status=401
```

既存56testsのpassは上記未カバー経路の成功を証明しない。live evidence元のraw応答は本reviewではアクセスしていない。

## 🔧 修正と次段階

| 優先度 | アクション | 理由 |
|---|---|---|
| P1 | 深いMCP contentを一つの正規化経路で展開し全identity/statusを検査 | envelope形で成功判定が変わる断絶を解消 |
| P1 | page detailのid/type/bodyを検査して不完全をmanifestへ伝播 | 表示だけcompleteのバックアップを防ぐ |
| P2 | receiptに成功とHTTP statusの整合性契約を加える | 公開証跡の矛盾を入口で拒否 |

相互批判で他2者の指摘との重複・対立を評価する。修正後は新commitの固定snapshotで既存testsと上記回帰を再確認して再reviewする。本書は初回独立レビューのみで、最終MAGI合意ではない。
