# MAGI 初回独立レビュー — CASPAR

- 視点: 性能・検証効率・取得完了判定
- 対象: `5a65fe111afb187e28459ec78931d9a9605c5098`
- baseline: `7f05b0c0` / public `icloudaichi/utage-mcp-guide`
- 検査対象: `private/review-initial` の固定スナップショット
- レビュー証拠の確認時刻: 2026-10-03 07:18 UTC
- 実規程: `installed prompts/magi_reviewer.md` と `installed skills/magi_reviewer/SKILL.md` を全文読了。
- 独立性: 他レビュー結果未参照。ネットワーク・実サービス・credential にアクセスせず、コードを編集せず、Python 標準ライブラリの mock で再現。
- 日報規程の適用範囲: ユーザー明示 PR critical review に合わせ検証コスト・完了判定へ適用。個人目標の推定・他 repo の config 更新は対象外。今回以前の同種 PR レビュー履歴は提供されていないため、同一指摘連続日数は評価不能。

## 判定

**変更が必要。P1 1 件、P2 1 件。P0 は確認していない。** 既存 56 tests は pass だが、ページ内容の欠落を complete と扱うケースが未検証である。

### ❌ P1 — 空のページ詳細を complete と扱う

位置: `backup/scripts/backup_funnels.py:225`（変更行）。関連 `:232-240`, `:441-443`。

`backup_page` は `data` が dict なら `{}` も受理する。`content_type` を `elements`、欠落した `elements` を `[]` へ補完し、True を返す。したがって API が項目を欠落した 200 応答を返しても空本文が保存され、今回追加された manifest は `status: complete`、終了コード 0 となる。バックアップの取得完了を証明できず、内容が取得できなかった利用者に成功を返す。

再現（全値は合成、`api_get` と config と sleep を mock）:

1. funnels: f1 1 件、total 1、per_page 100、current_page 1。
2. steps: s1 1 件、pages: p1 1 件。
3. p1 detail: `{"data": {}}`。
4. 観測: exit 0 / manifest complete / errors 0 / page の elements `[]` / 成功 banner。呼出し数 4。

修正案: 公開仕様から確認したページ詳細の必要項目・型と要求した resource identity を検証してから成功にする。欠落応答・異なる page ID・content_type に対応する本文キーの欠落は errors へ加算し、manifest と終了コードを incomplete にする。正しく取得した空 elements と欠落 elements を区別する regression test を追加する。

### ❌ P2 — ページ詳細が失敗しても step は complete と残る

位置: `backup/scripts/backup_funnels.py:355`（変更行）。関連 `:368-373`。

step の `status` を page list 取得直後の `pages_ok` だけで決め、詳細取得前に書く。detail の取得が後で失敗すると全体 manifest は incomplete になるが、その step の `_meta.md` は complete のままである。step 単位で復旧・再利用する消費側へ矛盾した完了マーカーを渡す。

再現（全値は合成、transport 等を mock）: funnels 1 / steps 1 / pages 1 / page detail `None` → exit 1 / global manifest incomplete / errors 1 / `Page.md` status error / step `_meta.md` status complete。

解釈の仮説 A: status は一覧取得のみの成功を意図する。この場合 `page_list_status` など意味を明示すれば矛盾を避けられる。仮説 B: status は step のバックアップ完了を意図する。この場合 detail 終了後に集約し、失敗が 1 件でもあれば incomplete にする。実装の質問をユーザーへ追加する必要はなく、コード側で完了マーカーの意味を明示すればよい。

修正案: page list の状態と detail 完了状態を分けるか、全 detail を処理した後に step status を更新する。実際の `backup_funnel` を通す失敗 test で global/step/page の状態を照合する。

## 既存制約として再現した事項

同一／sanitize 後同一タイトルの出力 collision は baseline にも存在する。タイトル `A/B` と `A:B`、異なる p1/p2、正しい detail を与えると 2 件取得後に `A_B.md` 1 件だけ残る。今回追加した complete manifest は errors 0 を報告する。新規の filename defect としては指摘しないが、complete が「取得成功」だけなのか「全 resource が独立ファイルとして保存された」まで保証するのかを説明する必要がある。高信頼バックアップを保証するなら ID をパスに含めるか collision を失敗扱いにするのが適切。

## ◎ 評価できる点

- 2026-10-03 receipt の 07:00:36 UTC に direct REST reference と existing OAuth proxy reference を各 1 回だけ記録し、LBS/Wasa の共有 read を再利用している。実サービスの追加呼出しを抑えつつ、接続経路の代表証拠を残せている。今回レビューは共有 read の真偽を新たな live 呼出しで再確認していない。
- `fetch_all_funnels:150-178` の件数・ページ・重複・total 不変検査は、短いページを後続ページで帳尻合わせする誤判定まで拒否する。不要な全再取得を行う前に異常を止める設計で、56 tests は 0.045 秒で実行完了した。
- `docs/tool-catalog.md:3` と `docs/endpoint-testing.md:11` は metadata 発見と完全 schema 確認を分ける。inputSchema/outputSchema/annotations 未捕獲を隠していないため、253 metadata が全 endpoint schema の成功証拠へ膨らまない。
- `docs/endpoint-testing.md:20-29,47-49` は blocked auth、商品設定と個別契約、offline と live、write 未実行を区別する。取得不能を再認証や大量 read へ拡張せず、未検証を保存する点は検証コストに対して適切。

## 再現と検証の範囲

`PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v` → **56 tests / 0.045s / OK**。

追加の 3 synthetic mock scenarios は上記の空 detail、detail failure、path collision。追加 tests の pass を主張していない。実 API の schema 適合・実 backup・133 write の本番動作は未検証のままである。

## 統合時に提案する優先アクション

| 優先度 | アクション | 期限 | 根拠 |
|---|---|---|---|
| P1 | ページ詳細の必要項目・resource identity・本文型を検証し欠落を incomplete にする | 修正後再レビュー前 | `{data:{}}` が exit 0 / complete |
| P2 | step の完了状態を detail 結果へ連動させるか一覧状態として明示する | 修正後再レビュー前 | step complete と global incomplete の再現 |
| P2 | complete の保存範囲を明示し collision の既存制約を記録する | PR 説明確定前 | 2 resource が 1 file へ上書きされる既存制約 |

未確定事項: live runner・全 schema・resource-specific 本文型をこのスナップショットで取得していない。ユーザーの個人目標について質問する必要はなく、レビュー要件の未確定として保存する。相互批判と修正後 pinned commit の再レビューは次工程。
