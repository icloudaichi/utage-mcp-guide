# MAGI BALTHASAR 相互批判（初回snapshotのみ）

対象固定commit `5a65fe111afb187e28459ec78931d9a9605c5098`。自身の初回独立reportを確定後、`private/magi-caspar-initial.md` と `private/magi-melchior-initial.md` を読んだ。修正中working treeは読んでいない。ネットワーク・実サービス・credentialアクセス、コード編集なし。

## CASPARへの批判・補完

- **P1空page detailは同意**。3者が固定snapshot上で別々に再現できた。API GET成功と復元用本文の取得を同一視する問題であり、BALTHASARのB1と統合する。別ID・HTML本文欠落への拡張は同じ根本原因で、修正回帰の対象へ含めるのが適切。正規に空の本文は失敗ではないため、field欠落と空値を区別する。
- **P2 step completeの意味は同意**。自身も `steps → pages → detail=None` をmockし、`errors:1`とstep `_meta.md`の`status: complete`が同時に残ることを再現した。global manifestは既にincompleteになるためP1へは上げない。`page_list_status`として限定する解釈A、step本文取得完了を示す解釈Bの両方が可能だが、保存状態を将来の復旧担当者が独立に消費することを考えると、list状態を別fieldへ分離し、全detail処理後にstep状態を集約する方が誤認を減らす。
- **filename collisionは適用境界を維持**。baselineにもあるため新規回帰として断定しない。今回のmanifestが完全な復元可能性を意味するなら、既存衝突もその契約と矛盾する。仮説Aは今回のcompleteが通信取得の完了だけを指す設計、仮説Bは全resourceの保存完全性を指す設計。今回スコープで全保存形式を改造する必要はないが、既知制約とcompleteの保証範囲を文書に明示するか、IDで独立保存する修正を選ぶべき。新規P1と同じ緊急度にはしない。
- **検証効率の評価は妥当**。56 testsは短時間で再現でき、追加実readは不要。目標がendpoint evidence整備なので、大量取得をしない点を性能低下と誤解していない。

## MELCHIORへの批判・補完

- **P1 nested JSON-RPC `result.content`は同意し、自身でも全4例を再現**。非JSONtext・wasamagazine profile・HTTP500・success signalのみが `True None None` になる。根拠は標準的なMCP CallToolResult envelopeがroot限定で処理される点で、単なる未知providerの想像例ではない。汎用MCP/JSON-RPC契約を名乗る新moduleへ適用する優先度P1は妥当。
- **当日のlive証跡への影響は限定して述べるべき**。このレビューはraw観測を読んでおらず、既存proxyがresult.contentだったと確認していない。receiptが既に誤っていると断定せず、「今後この形を渡すと誤成功し、公開helperの契約が形依存になる」と記載する。仮説Aは当日のroot text-listのみ、仮説Bは将来のclient JSON-RPC result.content利用。どちらでもoffline修正は必要で、追加live確認や再認証は不要。
- **P1 backup detailはCASPAR/BALTHASARと統合**。page identity・content type・本文fieldを明示した回帰は、成功を他担当者へ移転するために必要。実サービスの実backup成功をこの修正から推定しない。
- **P2 success receipt HTTP矛盾は同意**。自身のB2と重複するため一件として扱う。通常のunwrap経由なら401は拒否される境界を明記し、実証拠偽造と誤解させない。null statusは共有証跡の未保存を表すため2xxへ補完しない。
- **`types_only_projection`のpositive評価はその関数に限定すれば妥当**。一方、公開fixtureの形が別フォーマットで、そのwalk guardが動的キーを通すため、関数の安全性をfixture全体の安全性へ広げない。BALTHASAR B3の固定field/structural key検証を追加して初めて、今後更新時のprivacy guardとして繋がる。現在fixtureに秘密漏洩を検出したという主張はない。

## 3者で統合すべき優先順位

1. **P1**: nested MCP contentの完全な正規化・全branchのidentity/status/error検査。非JSON/誤profile/HTTPerror/success-onlyの誤成功を止める。
2. **P1**: page detailのID・type・本文field検証。欠落/別resourceをmanifest completeへ進めない。
3. **P2**: step状態をdetail取得結果へ連動、またはlist状態と明示的に分離。global/step/pageを一回のmock flowで照合。
4. **P2**: success flag型とreceipt HTTP整合性、fixture key固定検証。正常なnull HTTP/shared receiptを壊さず誤成功・future privacy漏れを防ぐ。
5. **P2/既存制約**: filename collisionとcomplete保証の範囲を明示。IDを使用する設計は将来の復元可能性向上に有効だが、endpointの本番検証へ範囲を拡大しない。

これらの修正は全てofflineで具体化できる。ユーザーへの追加質問・新credential・実writeは不要。公開前に新固定commitのsnapshotで回帰と3者再レビューを行い、初回56passを最終承認へ流用しない。

## 未確定事項

公式web仕様と当日のraw live応答はネットワーク/credential禁止のため、このレビューが再実証していない。個別契約status/次回課金/外部subscription IDは未露出・未取得の境界を維持する。現在進行中の修正が完了したとは本書では判断しない。
