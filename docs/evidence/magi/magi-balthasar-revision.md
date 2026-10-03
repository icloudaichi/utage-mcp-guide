# MAGI BALTHASAR 修正後独立レビュー

- 判定: **changes_requested**。初回・相互批判の具体指摘は修正確認済み。追加探索でprivacy回帰のP2を1件検出した。
- 対象固定commit: `497bacc46b7ca412e9fc0959ff37462720e772d6`。
- 比較対象: 初回 `5a65fe111afb187e28459ec78931d9a9605c5098`。
- 読取対象: `private/review-revision` 固定snapshotと両commit間diff。他2者のrevision reportは読んでいない。
- 実prompt/skillは初回に全文読了済み。本来の日報レビューを明示依頼どおり保守・証拠・スキル移転へ適用。task目標のみ推定扱いを維持し、個人目標は変更していない。
- ネットワーク・credential・実サービス・repoコード編集なし。Python標準libraryのmock、一時directoryの合成fixtureのみで検証した。

## ❌ R1 / P2: anonymous fixture guardが生の数値をschema fieldに許す

- 位置: `tests/test_catalog_snapshot.py:83-84`。関連 `:61-69`、`:88-92`。
- 根拠: keyは固定allowlistへ改善したが、数値に対する検証は場所によらず `assertIsInstance(value, int)` のみである。`count`や`length`に必要な構造数値と、業務schemaの実額・数値IDを区別していない。
- 独立再現: temporary rootに `tests/fixtures/synthetic-shape.json` を作成し、当該test moduleの `ROOT` だけをmockして、実際の `test_fixtures_are_only_anonymous_shape_not_response_values` を呼び出した。合成fixtureは下記。

```json
{"origin":"observed_types_only","case":"synthetic","tool":"payment_product_detail_get","shape":{"object":{"amount":123456,"id":9281}}}
```

- 実結果: testはpassする。動的Bearer/contract/phone keyの拒否回帰も実行された上で、上記の生数値fixtureを受理した。
- 影響: 公開fixtureは実額・決済ID・会員情報を保持しないという継続運用のguardが、数値型の値に対して効かない。現在のfixtureに実額や実IDがあることを検出したものではなく、将来更新時に混入しても検出できない問題である。
- 修正案: 整数は `count`/`length` など明示した構造位置にのみ許可し、`object`内schema fieldは型タグまたは入れ子shapeのみを許可する。boolをintegerとして受理しない。生のsynthetic amount/idが失敗し、正規count/lengthがpassする回帰を追加する。
- 判断の範囲: P0/P1の新欠陥は検出していない。R1は変更されたprivacy guardが将来担当者へ渡す契約の不足であり、追加live/API readは必要ない。

## 初回・相互批判の解消確認

| 指摘 | 確認した修正・再現 | 判定 |
|---|---|---|
| B1/CASPAR/MELCHIOR page detail欠落→complete | `backup_page:239-246`でid一致/type/body型を検査。自身の初回と同じ空detail flowはexit1/manifest incomplete/errors1/step incomplete | 解消 |
| CASPAR step statusの矛盾 | `backup_funnel:367-389`で全detail処理後にstep状態を集約。detail Noneもexit1/global+step incomplete。正規空bodyはexit0/complete | 解消 |
| CASPAR既存title collision | `resource_basename:209-215`で元IDのSHA-256 full digestをsuffixに使用。2同名funnel×2同名step×2同名pageが8独立ファイルとなるmock回帰pass。multibyte filename保存回帰もpass | 解消 |
| MELCHIOR nested JSON-RPC content誤成功 | `contract_checks:289-355`で各depthを共通処理。自身が4ケースを再実行し非JSON→invalid_result、別profile→profile_mismatch、HTTP500→http_error、success-only→invalid_result | 解消 |
| B2 nonbool success | `contract_checks:181-185`。`success='false'` + synthetic dataはinvalid_resultへ変化。business recordのstatus/successとwrapperは区別する回帰pass | 解消 |
| B2/MELCHIOR HTTP401成功receipt | `contract_checks:386-399`でHTTP整合・元tool/profile binding・payload evidenceを再検査。初回直接構築はinconsistent_http_successへ変化。null HTTP共有証拠は許容 | 解消 |
| B3 fixture dynamic key | `test_catalog_snapshot:61-87`で固定schema/structural keyと匿名番号pattern以外を拒否。synthetic Bearer/contract/phone key回帰pass | 動的キーの問題は解消、数値位置のR1を追加 |

## ◎ 継続運用への評価

- **証拠の矛盾を入口で止めた**。receipt生成が元planのtool/profileとpayloadを再確認するため、transport追加や担当者交代時に手動successだけが証拠へ移転される危険を減らす。HTTP未保存を2xxへ推定しない設計も維持している。
- **状態を実取得へ連動させた**。全detailが終わってからstep completeを書くことで、復旧をstep単位に分ける担当者もglobal manifestと同じ失敗を把握できる。
- **初回レビューを消さず証跡化した**。初回6reportについて、private sourceと公開reportのSHA-256が `docs/evidence/magi/provenance.json` の両hashに一致することを全件確認した。修正前に承認していなかった履歴が残り、レビュー形骸化を防ぐ。
- **診断失敗を成功へ上書きしていない**。13receipt目までを確認し、2026-10-03 `07:02:26.425579+00:00` の非JSON診断は `status:unverified`, `failure_marker:provider_non_json_text`。正しいdetail_idによる後の成功とは独立して残る。

## テストと追加再現の結果

固定snapshotで `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v`:

```text
Ran 70 tests in 0.068s
OK
```

自身の追加合成再現:

```text
nested_plain         False invalid_result None
nested_wrong_profile False profile_mismatch None
nested_http500       False http_error 500
nested_success_only  False invalid_result None
nonbool_success      False invalid_result
http401_receipt      inconsistent_http_success
empty_detail         exit1 incomplete errors1 step_complete=False
detail_failure       exit1 incomplete errors1 step_complete=False
valid_empty_body     exit0 complete errors0 step_complete=True
numeric_amount_and_id_fixture_guard_accepted True
```

最後の行がR1の根拠であり、70passをprivacy contract全域の成功と扱わない。

## 残る制約と未確定事項

- inputSchema/outputSchema/annotationsは未捕獲、timezoneは未確定、`created_at`と`submitted_at`を分離したまま。完全schema適合を承認しない。
- 個別契約status・次回課金・外部subscription IDは対象接続metadata範囲で未露出/未取得。UTAGE全体で絶対不可と推定しない。
- 共有auth blocked、実write0、実backup未実行を維持。公式リンク内容とraw live responseの独立再取得はこのreviewで行っていない。
- 運用解釈の仮説Aは今回fixtureが手動生成され毎回別private scanもする設計、仮説Bは公開testを将来担当者の匿名化gateとして使用する設計。R1の構造位置検証はどちらでも有効で、ユーザーの個人意図へ質問する必要はない。

R1のoffline修正と新固定snapshotの再確認後に承認判断を更新できる。本reportは当該commitに対する独立判定で、他2者の合意や最終PR承認を代行しない。
