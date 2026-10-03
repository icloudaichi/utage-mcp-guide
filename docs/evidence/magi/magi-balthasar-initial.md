# MAGI BALTHASAR 独立レビュー（初回）

- 対象: `icloudaichi/utage-mcp-guide` 固定コミット `5a65fe111afb187e28459ec78931d9a9605c5098`、baseline `7f05b0c0`。
- 読取元: `private/review-initial` 固定スナップショット。別reviewerの結果は参照していない。
- 実指示: `installed prompts/magi_reviewer.md` と `installed skills/magi_reviewer/SKILL.md` を全文読了。
- 本来の日報レビューを、ユーザーの明示PR critical review依頼に従い、保守・根拠・継続運用へ適用した。
- 目標は `private/magi_config/current_goals.md` のtask由来の推定のみ。個人目標・日報・他repoは変更していない。
- ネットワーク・credential・実サービスにはアクセスせず、コード変更なし。オフラインmock確認のみ。

## 判断

P0は検出なし。P1が1件、P2が2件。成功証跡を誤生成できる経路を修正し、修正後レビューが必要。

### ❌ B1 / P1: 空のページ詳細でも完全バックアップと宣言する

- 位置: `backup/scripts/backup_funnels.py:225-237`、`441-443`。
- 根拠: ページ詳細は `data` がdictであれば受理する。`{"data":{}}` では `content_type` を `elements`、要素を `[]` と補完し、page IDも一覧メタデータを補完するため、ページ取得を成功扱いする。
- 再現: 固定スナップショットで `load_config`・`fetch_all_funnels`・`api_get`・`time.sleep` をmock。正しい1ファネル/1ステップ/1ページ一覧の次にページ詳細 `{"data":{}}` を返す。実通信なし。
- 実結果: `main()` はexit code 0、manifestは `{"status":"complete","errors":0,"failure":null}`。
- 影響: API応答の欠損や仕様変化に対して、復元対象の内容を保存していなくても、新設したmanifestが完全性を保証する。今後他者にバックアップ実行を引き継ぐ際に、実行者が不足を察知できない。
- 修正案: ページdetail IDと期待IDを一致検証し、公式応答の必要な `content_type` とそのタイプ別内容フィールドを検証する。空dict/ID相違/必要フィールド欠落を `False` としてmanifest incompleteへ伝播するmock回帰を追加する。

### ❌ B2 / P2: 成功receiptの不変条件がHTTP statusと結び付いていない

- 位置: `scripts/contract_checks.py:179-184`、`368-375`。
- 根拠: `success` が文字列 `"false"` 等の場合は `is False` に合致せず、データが存在すれば `unwrap_result` は成功にする。また `make_receipt` はmarker/successの一致を検証するが、成功とHTTP非2xxの矛盾は検証しない。
- 再現1: `unwrap_result({'success':'false','data':[{'id':'synthetic'}]}, expected_tool='find_tools', expected_profile='lbs').success` は `True`。
- 再現2: `make_receipt(build_read_plan('find_tools','lbs'), CheckedResult(True,None,401,{}), verification_kind='live_read')` は `status='success', http_status=401` のreceiptを生成する。
- 影響: 現在の正常な `execute_read_plan → unwrap_result` 経路はHTTP 401を拒否するが、外部観測から `CheckedResult` を組み立てる引き継ぎや別transport追加では、意味の矛盾した成功証跡を公開できる。
- 修正案: envelopeの `success` は存在するときboolのみ受理し、成功receiptに非2xxのHTTP statusがある場合は拒否する。HTTP status未保存/nullは現在の共有read証跡と同じく許容し、未保存を2xxに補完しない。

### ❌ B3 / P2: fixtureのprivacy回帰が動的キーを許している

- 位置: `tests/test_catalog_snapshot.py:60-71`。関連 `scripts/contract_checks.py:27-37`、`385-418`。
- 根拠: fixtureのdict keyは `@` だけを禁止しており、それ以外の任意文字列を受理する。一般投影関数は固定schema名以外のキーを落とすが、公開fixtureは別形式であり、この固定allowlistをテストで共有していない。
- 再現: 現在の `walk` と同じ判定を `{'object':{'Bearer synthetic-token':'str','contract_synthetic_9281':'str'}}` に適用するとpass。実秘密は使用していない。
- 影響: 次回更新時に金額・token・契約ID・会員情報がdynamic keyへ残っても、匿名shape検証が緑になる。現在公開されているfixtureにその漏洩があると判断したものではない。
- 修正案: fixture形式の構造キーと公開可能なschema名を明示的に固定し、未知キーは `[other-fields]` 等の匿名集約だけへ移す。生成関数とfixture検証のallowlistを共有し、synthetic token/契約ID/電話/氏名のdynamic key回帰を追加する。

## ◎ 評価できる点

- 2026-10-03 `06:55:35.934312+00:00` のcatalog観測を253 metadata件へ固定し、input/output schema・annotations未捕獲を各ツールにも明記した。metadata発見をschema確認へ誤変換しない点は、次回更新の再現性に資する（`docs/evidence/tool-catalog-2026-10-03.json:1-35`、`docs/endpoint-testing.md:11`）。
- 共有readの結果を再利用し、2026-10-03 `06:21:23.858470+00:00` のhirahara auth errorを維持した。再認証や別接続fallbackで結果を上書きせず、対象接続の制約を次の担当者が把握できる（receiptケース `daichi-account-read-status-0`）。
- 商品価格設定と個別契約・次回課金・subscription IDを分離した。2026-10-03 `07:03:04.516039+00:00` の正しい `detail_id` readと、誤った `product_detail_id` の `-32602`を独立記録し、後の成功で失敗を消していない（`payment/SKILL.md:17-19`、receipt）。
- 標準Pythonのみ、credential不要で56 offline testsを再実行できた。business write 133件はtransport前に拒否するため、今後の担当者へ安全に検証手順を移転できる（`tests/test_catalog_snapshot.py:34-43`）。
- TLS検証無効化と全認証cache削除の手順を撤去した。復旧を急いだ際に他の接続やセキュリティ設定を壊す運用が文書へ定着するのを防いでいる（`setup/SKILL.md:98-112`）。

## ⚠️ 解釈が未確定の点

- fixture生成の範囲: 仮説Aは今回の証跡を一度だけ安全に変換するため、private生成処理を公開しない設計。仮説Bは将来の更新も公開helperへ移管する設計。公開helperとfixtureの形式不一致は確認済みだが、どちらの運用意図かは断定しない。B3の固定allowlist検証は両設計で有効であり、ユーザー確認は不要。
- 新manifestの狙い: 仮説Aは件数・取得失敗を中心とする運用上の完了状態。仮説Bはバックアップ内容の完全性まで保証する状態。文書は「不完全な取得を完了扱いしない」と記載するためB1を優先する。内容検証の最小追加はどちらの意図でも必要で、ユーザー確認は不要。
- 公式URLの内容はレビュー中に再取得していない（ネットワーク禁止）。仕様の正確さはこのレビューが独立実証したと表現しない。
- 個別subscriptionツールはこの接続metadata範囲で未露出であり、UTAGE/MCP全体で絶対不可と判断しない。

## 引き継ぎアクション

| 優先度 | アクション | 期限 | 根拠 |
|---|---|---|---|
| P1 | ページ詳細のID・content_type・内容必須条件を検証してincompleteへ伝播 | 初回PR公開前 | B1、空dictでexit0/complete再現 |
| P2 | 成功flag型とreceipt HTTP整合性を固定 | 修正後レビュー前 | B2、false/401成功再現 |
| P2 | fixture key allowlistと匿名生成ルールを共有しprivacy回帰を追加 | 修正後レビュー前 | B3、synthetic dynamic key通過 |

## 検証結果

`PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v`: 56件pass（固定初回スナップショット）。追加の再現は全てmock/一時ディレクトリで実施し、ネットワークなし。これらは本番schema適合・write成功・バックアップ実サービス成功の証拠ではない。

相互批判と修正後の固定コミット再レビューは未実施。本レポートは初回独立レビュー結果のみ。
