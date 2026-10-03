# MAGI 修正後独立再レビュー — CASPAR

## 判定

**approved** — 対象 revision `497bacc46b7ca412e9fc0959ff37462720e772d6`。初回・相互批判で確認した CASPAR の P1/P2 は再現しなくなった。今回の独立検査で、新たな対応必須 P0/P1/P2 は確認していない。

承認はこの PR の文書・offline 契約・バックアップコード修正に対する判断であり、全 endpoint の本番動作、全 JSON Schema、個別課金契約 read の実証ではない。

## 独立性と範囲

- 比較元: initial `5a65fe111afb187e28459ec78931d9a9605c5098`。
- 検査: `private/review-revision` の固定 snapshot と `private/review-initial` の差分。
- 確認時刻: 2026-10-03 07:31 UTC。
- 他者の revision report と修正版 workingtree は未参照。
- 実規程の初回全文読了を継続適用。性能・検証効率・取得完了判定が担当範囲。個人目標の推定は行わない。
- ネットワーク・実サービス・credential アクセス 0。コード編集 0。再現は Python 標準ライブラリの mock と純関数呼出しのみ。

## 各指摘の再検証

| 初回／相互批判 | 修正位置 | 修正版で独立に得た結果 | 状態 |
|---|---|---|---|
| P1: `data:{}` の detail が空本文を作って complete | `backup/scripts/backup_funnels.py:237-246` | 同じ 1 funnel→1 step→1 page→空 detail の mock は exit 1、global incomplete/errors 1、page error。空本文を補完しない | 解消 |
| P2: detail 失敗でも step complete | 同 `:367-389` | detail `None` と空 dict の両ケースで step incomplete/errors 1。global/page と一致 | 解消 |
| baseline 由来の title collision と新 complete の制約 | 同 `:209-215,231,312,352` | `A/B` と `A:B` の p1/p2 は 2 ファイル保存され、両 ID を保持。exit 0 / complete | 解消 |
| P1: nested JSON-RPC result.content の nonJSON/wrong profile/HTTP500/successのみが成功 | `scripts/contract_checks.py:287-355` | 各ケースが順に invalid_result / profile_mismatch / http_error(HTTP 500保持) / invalid_result。success は false | 解消 |
| P2: wrapper success が string `false` でも成功 | 同 `:181-184` | `success:'false',data:[]` は invalid_result / false | 解消 |
| P2: manual CheckedResult success+HTTP401 が live receipt | 同 `:383-399` | 元の `make_receipt(...CheckedResult(True,None,401),live_read)` は inconsistent_http_success を返す | 解消 |
| 適用境界の懸念: resource status/flag を tool error と混同 | 同 `_error_marker` の wrapper 判別 | resource list の status='failed' / success=false は read 自体の成功として受理。wrapper success=false は tool_error | 解消 |

`backup_page` の ID・content_type・本文キーの検査は、正しく取得した空 elements/空 raw_html と、本文の欠落を区別する。修正済み regression は別 page ID、missing content_type、invalid type、本文欠落・型違い・一覧との content_type 不一致を拒否している。

## 追加境界検査

次の synthetic ケースを既存 tests に加えて手動実行した（テストコードは snapshot に追加していない）。

- 正常 MCP content を result で 0/1/4/16/30 段ラップしても、最終 payload は `{tools:[]}`。content 配列を business payload として保存しない。
- structuredContent が正常でも、別 result 内の profile 不一致を拒否。
- structuredContent が正常でも、別 body 内の nonJSON content を拒否。
- 外側 HTTP200 と content 内 HTTP500 の競合は http_status_mismatch。
- body→result→content の success=false は tool_error。
- checked result の payload を削除すると invalid_result_evidence、profile/tool を変えると result_binding_mismatch、identity binding を guessed にすると invalid_result_binding。
- HTTP status が捕獲されていない正しい payload の receipt は HTTP null を保持する。HTTP200を捏造せず、schema_verified は false のまま。

## テストと効率の評価

`PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v` → **70 tests / 0.073 秒 / OK**。

◎ 初回 56 tests から追加された 14 件は空 detail、本文の型・identity、step status、collision、nested MCP、boolean 型、receipt binding を扱う。修正の不具合経路を対象にしており、実サービスの大量再取得をせず判定の信頼性を改善できた。

◎ ID の UTF-8 原文から SHA-256 を計算するため、同名と sanitize 後同名だけでなく ID の lossy escape 衝突も避けられる。長い日本語の label は byte 数を抑え、255-byte 以下のファイル保存 test が通過。読める label と一意の保存先を両立している。

◎ 全 wrapper に同じ decoder を適用してから receipt の binding/payload/HTTP を再確認する。特定エラー文だけへの分岐追加より組合せの取りこぼしを抑える構成で、検査時間は依然として 1 秒未満。

◎ fixture の schema key whitelist を test で限定し、Bearer 文字列・決済 ID 形式・電話番号の dynamic key を拒否する検査が通過した。現在の fixture を匿名型構造として確認した。private credential literal scan は、この reviewer では credential アクセスを禁止されたため独立再実行していない。公開 privacy receipt 自体も「完全な秘密不存在証明ではない」と制限を記載する。

## 未検証事項と承認の限界

- `inputSchema` / `outputSchema` / annotations の全体は未捕獲のまま。253 件は LBS 1 接続の metadata として記載され、全 schema 適合へ格上げされていない。
- timezone 保証と `submitted_at` の公開保証は未確認。offset のない日時を JST/UTC に推定変換したり期日判定へ使わない文書上の境界を維持。
- 商品 plan 設定から、購入者の個別 subscription status / 次回課金 / 決済代行 subscription ID を取得・推定した扱いにしていない。
- `payment-read-regular-plan-detail-diagnostic` の追加 receipt は `unverified` / `provider_non_json_text`、先の未確認応答も `provider_result_unverified`。成功した detail_id read と独立した失敗・未検証の証跡を保持する。
- blocked auth は成功へ変換せず、再認証・他 profile fallback を行った記録にしていない。
- 全 133 write の実サービス動作、実 backup、API schema 全適合は未検証。70 tests の成功は offline contract の成功としてのみ扱う。

既知の制約をこの承認から消していない。新しい live call・権限・runtime install が必要なブロッカーはなく、この pinned revision への対応必須 review findings は 0 件。
