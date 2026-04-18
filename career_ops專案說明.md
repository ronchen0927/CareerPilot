# Career-Ops 專案說明

> 個人化的 AI 求職指揮中心 — 把 AI 交給候選人，讓候選人來「挑選」企業。

## 一句話描述

將 Claude Code（或 OpenCode）轉化為完整的求職管道：**評估職缺 → 生成客製履歷 → 自動掃描職缺平台 → 追蹤應徵狀態**，全部在本地端，單一資料來源。

## 為什麼存在

企業用 AI 篩候選人，那候選人為什麼不能用 AI 反向篩企業？

作者 [Santiago](https://santifer.io) 用這套系統：
- 評估了 **740+ 份職缺**
- 生成 **100+ 份 ATS 最佳化履歷**
- 最終拿到 Head of Applied AI 職位

然後開源，讓其他求職者也能用。

## 核心設計哲學

### 1. 這是篩選器，不是廣撒網工具

系統**強烈建議不要應徵低於 4.0/5 的職缺**。品質 > 數量。你和招募人員的時間都很寶貴。

### 2. 人機協作 — AI 絕不自動送出應徵

AI 負責：評估、草擬、填表、生成 PDF、找聯絡人。
你負責：**最終按下 Submit**。送出前永遠會停下來讓你審閱。

### 3. 系統越用越懂你

初期評估可能不準，因為它還不認識你。餵它：履歷、職涯故事、成就佐證、你的偏好與地雷。把它當作新進的招募顧問 — 第一週在學習你，之後變成不可或缺的夥伴。

### 4. 自我修改

這個系統**設計上就是給 AI Agent 改的**。職位類型不對？提示 Agent 改 `modes/_profile.md`。想換語系？請它翻譯 `modes/` 資料夾。

## 架構分層（最重要的規則）

| 層級 | 誰寫？ | 範例檔案 |
|------|-------|---------|
| **User Layer**（使用者資料） | 你 / Agent 為你 | `cv.md`、`config/profile.yml`、`modes/_profile.md`、`portals.yml`、`data/*`、`reports/*` |
| **System Layer**（系統骨架） | 官方更新 | `modes/_shared.md`、所有 `modes/*.md`（除 `_profile.md`）、`*.mjs`、`dashboard/` |

**鐵則：** 任何使用者客製化（職位類型、敘事、談判腳本、薪資目標）一律寫到 **User Layer**。這樣系統更新（`node update-system.mjs apply`）才不會覆蓋你的設定。

## 主要模式（Skill Modes）

| 觸發情境 | 模式 | 功能 |
|---------|------|------|
| 貼 JD 或 URL | `auto-pipeline` | 評估 → 報告 → PDF → 追蹤，一條龍 |
| 評估單一職缺 | `oferta` | A–F 結構化 10 維評分 |
| 比較多份職缺 | `ofertas` | 排序與取捨 |
| LinkedIn 外聯 | `contacto` | 找聯絡人 + 草擬訊息 |
| 深度研究公司 | `deep` | 公司現況、戰略、文化 |
| 面試準備 | `interview-prep` | 公司情報 + STAR+R 故事 |
| 產出 CV | `pdf` | 針對特定 JD 最佳化 ATS |
| 評估課程/證照 | `training` | 對目標路徑的投資報酬 |
| 評估作品集專案 | `project` | 對職涯品牌的貢獻度 |
| 應徵狀態總覽 | `tracker` | 管道看板 |
| 填表助手 | `apply` | 協助填應徵表單（不送出） |
| 掃描平台 | `scan` | 零 Token 掃 Greenhouse/Ashby/Lever |
| 處理待辦 URL | `pipeline` | 清空 `data/pipeline.md` 收件匣 |
| 批次處理 | `batch` | 並行 worker 評估多份 |
| 分析被拒模式 | `patterns` | 改善目標設定 |
| 追蹤跟進時機 | `followup` | 該何時寄追蹤信 |

## 評估報告結構（Block A–G）

每份評估報告包含：

- **A. 職位摘要** — 分類為 LLMOps / Agentic / PM / SA / FDE / Transformation
- **B. 履歷匹配** — 契合度推理（非關鍵字比對）
- **C. 職級策略** — 這職缺對你是升遷、平調還是後退
- **D. 薪酬調查** — 地區薪資、談判空間
- **E. 個人化** — 你應該強調什麼、避開什麼
- **F. STAR+R 面試準備** — 預期問題與回答骨架
- **G. 職缺合法性** — 用 Playwright 驗證職缺是否還活著

## 預設掃描範圍（45+ 家）

- **AI 實驗室：** Anthropic、OpenAI、Mistral、Cohere、LangChain、Pinecone
- **語音 AI：** ElevenLabs、PolyAI、Parloa、Hume AI、Deepgram、Vapi、Bland AI
- **AI 平台：** Retool、Airtable、Vercel、Temporal、Glean、Arize AI
- **客服中心：** Ada、LivePerson、Sierra、Decagon、Talkdesk、Genesys
- **LLMOps：** Langfuse、Weights & Biases、Lindy、Cognigy、Speechmatics
- **自動化：** n8n、Zapier、Make.com

求職板：**Ashby、Greenhouse、Lever、Wellfound、Workable**。

可在 `portals.yml` 全部換成你想要的公司。

## 技術堆疊

- **執行環境：** Node.js (`.mjs` ESM)
- **瀏覽器自動化：** Playwright（PDF 生成 + 職缺抓取 + 合法性驗證）
- **設定格式：** YAML
- **資料儲存：** Markdown 表格 + TSV 批次檔
- **CV 範本：** HTML/CSS + Space Grotesk / DM Sans
- **儀表板 TUI：** Go + Bubble Tea + Lipgloss（Catppuccin Mocha）
- **代理：** Claude Code / OpenCode，自訂 skills 與 modes

## 關鍵指令

```bash
# 檢查環境前置條件
npm run doctor

# 驗證管道完整性
node verify-pipeline.mjs

# 正規化狀態
node normalize-statuses.mjs

# 去除重複
node dedup-tracker.mjs

# 合併批次追蹤新增項
node merge-tracker.mjs

# 掃描職缺平台（零 Token）
node scan.mjs

# 檢查職缺是否仍活著
node check-liveness.mjs

# 更新系統（不會動你的資料）
node update-system.mjs check
node update-system.mjs apply
```

## 狀態機（`templates/states.yml`）

| 狀態 | 使用時機 |
|------|---------|
| `Evaluated` | 報告完成，待決定 |
| `Applied` | 已送出 |
| `Responded` | 公司回覆了 |
| `Interview` | 面試中 |
| `Offer` | 拿到 Offer |
| `Rejected` | 公司拒絕 |
| `Discarded` | 自己放棄或職缺關閉 |
| `SKIP` | 不合適、不應徵 |

## 管道完整性規則

1. **不要直接編輯 `applications.md` 新增項目** — 寫 TSV 到 `batch/tracker-additions/`，用 `merge-tracker.mjs` 合併
2. **可以**直接編輯 `applications.md` 更新既有項目的狀態/備註
3. 所有報告 header 必須包含 `**URL:**` 和 `**Legitimacy:** {tier}`
4. 同公司 + 同職位永不重複建立 — 覆寫更新即可
5. 報告編號：3 位數零補齊，單調遞增（max+1）

## 多語系模式

- 預設：`modes/`（英文）
- 德語（DACH 市場）：`modes/de/` — 含 13. Monatsgehalt、Probezeit、AGG、Tarifvertrag 等在地語彙
- 法語：`modes/fr/` — 含 CDI/CDD、convention SYNTEC、RTT、mutuelle 等
- 日語：`modes/ja/` — 含 正社員、賞与、退職金、みなし残業、36協定 等

在 `config/profile.yml` 設定 `language.modes_dir` 即可切換。

## 道德使用（重要）

1. **絕不幫你自動送出應徵。** 送出前永遠停下讓你審閱。
2. **主動勸退低分應徵。** 低於 4.0/5 系統會明說「不建議」。
3. **品質 > 速度。** 瞄準 5 家勝過亂投 50 家。
4. **尊重招募人員。** 每份應徵都消耗某個真人的注意力。只送值得讀的。

## 配套資源

- **作者的作品集網站（也開源）：** [github.com/santifer/cv-santiago](https://github.com/santifer/cv-santiago) — 可 fork 改造
- **Discord 社群：** https://discord.gg/8pRpHETxa4
- **案例研究：** [santifer.io/career-ops-system](https://santifer.io/career-ops-system)

## 授權

MIT — 本地端工具，資料不離開你的機器，直接送到你選的 AI 供應商（Anthropic、OpenAI…）。官方不收集、不儲存、不存取任何使用者資料。
