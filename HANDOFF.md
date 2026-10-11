# HANDOFF

更新：2026-10-11 · by Claude · HEAD `4d18617`
<!-- 規則見 AGENTS.md「Handoff」。上限 150 行；過期內容移到 docs/archive/HANDOFF-YYYY-MM.md。 -->

## ▶ 下一步（只放一件，必須帶 #Issue）
#50 審查並落地 PR #54 中的 fail-closed 修正（缺少 control file 時 `install --check` 不再回報 CURRENT），之後跑 `nexus-certify issue-check --issue 50`。依據：最近更新的 open Issue（bug）；PR #54 為 clean、test 與 Nexus Core issue completion 皆綠。

## 進行中
- #50 / PR #54 Skill contract fingerprint 缺檔改為 not-current / `CONTENT_FINGERPRINT_MISMATCH`；待審查與合併。
- #51 / PR #54 同一 PR 也讓 `append_learning_event` 以 `learning-event.v1` 驗證，並把 `recommended_level` clamp 到 assessment ceiling；合併後需另跑 `issue-check --issue 51`。

## 待確認（沒有 Issue 號）
- spontaneous-capture 合約（#47、#49 已合併）之後的下一步產品工作，目前沒有 open Issue。

## 卡住 / 注意
- PR #1（`repolearn/g1-generic-contracts`，2026-09-15）仍 open 且有衝突（dirty），內容看起來已被後續 main 取代；需決定關閉或 rebase。
- PR #54 不使用 closing keyword，兩個 Issue 都要各自驗證後才能關。
- #50/#51 來自 Nexus-new 的跨 repo invariant 稽核，Issue 本身不是實作授權；合併需另行授權。
- 隱私邊界：使用者學習狀態與 mastery evidence 屬個人資料，不得寫入 repo 或 HANDOFF。
