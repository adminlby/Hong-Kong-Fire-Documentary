[English Version](#english-version)

# 11.26 大埔宏福苑火災紀錄庫

本存庫旨在整理及保存 2025 年 11 月 26 日大埔宏福苑火災的公開資料，包括新聞報道、影片紀錄、技術分析、承辦商資料、義工及社區支援資訊、官方回應，以及事件後續的相關資料。目標為建立一個公開、集中及可查證的紀錄庫，方便學術界、媒體、工程界及關注事件的市民查閱。

## 一、目的

- 記錄火災事件的公開資料（影片、新聞、文件）
- 建立清晰時間線，以便理解事件發展
- 整理與工程、物料科學及安全標準相關的技術分析
- 保存義工與社區在事件期間提供的支援資訊
- 將分散於不同平台（Threads、IG、Telegram、Google Docs 等）的資訊集中化
- 為外地人士、研究員及學者提供可核實的背景資料

## 二、事件概述

2025 年 11 月 26 日，大埔宏福苑發生嚴重火災，火勢在極短時間內迅速由低層蔓延至頂層，造成多人傷亡。事件引發社會對棚網物料、阻燃標準、維修工程管理及監管制度的廣泛質疑。事後，大量居民需要緊急撤離，區內義工、商戶及非政府組織迅速提供協助，包括物資、休息站、臨時寄養、清潔用品及其他支援。

## 三、存庫內容架構

主要內容存放於 `content/` 目錄下：

- **`/timeline/` 時間線**：按時序整理的事件發展紀錄，包括火災發生、救援過程及事後發展。
- **`/videos/` 現場片段**：收集自社交媒體及新聞的現場影片，附有來源連結。
- **`/news/` 新聞報道**：各大媒體的相關報道存檔，按媒體及日期分類。
- **`/analysis/` 技術分析**：整理有關棚架安全、物料阻燃標準及火災成因的技術文獻與分析。
- **`/support/` 支援資訊**：義工服務、物資捐贈及社區互助的相關資訊。
- **`/photos/` 圖片紀錄**：現場照片及相關圖片紀錄。
- **`/residents/` 居民討論**：收集居民在各平台的討論、互助訊息及聲音。
- **`/docs/` 官方文件**：
  - 政府部門回覆及公開信件
  - 宏福苑業主立案法團管理委員會會議記錄（2021-2025，共34份）：[PDF格式](content/docs/meeting_minutes/pdf/README.md) | [Markdown格式](content/docs/meeting_minutes/markdown/README.md)

## 四、主要研究與技術議題

本存庫將整理及分析以下議題：

- 竹棚與金屬棚架的物理特性及安全比較
- 香港棚網的法定阻燃要求及相關標準
- 承辦商於維修工程中的責任及管理制度
- 火勢於短時間內急速上升的可能機制
- 物料燃點、煙囪效應、工程流程及驗收制度
- 工程界、物料科學界、消防專業人士的公開意見

## 五、社區參與方式

歡迎市民、研究者或專業人士：

- 補充資料或來源
- 提交更正或更新
- 加入技術或政策分析
- 整理義工支援資訊
- 以 Pull Request 或 Issue 形式作出貢獻
  - 如你不熟悉 GitHub 的運作，我們建議你以 Issue 形式提議需更正的內容

### 提交文件時請提供以下資料 / Information to Include When Submitting Documents

為確保文件可作為有效證據，提交文件時請提供以下資料：

**1. 原始網址 (Original URL)**

- 文件的原始來源網址
- 如來源已失效，請註明並提供備份來源（如 Wayback Machine）

**2. 收集時間 (Collection Time)**

- 記錄您取得文件的時間
- 格式範例：`2025-11-27 14:30`（如未提供時區，則假設為香港時間 HKT）
- 如未提供，則假設為該文件首次提交至存庫的時間（原始 commit 時間）

**3. 檔案雜湊值 (File Hash) [建議 / Recommended]**

- 有助於驗證檔案的完整性，確保符合法律/存檔要求
- Mac/Linux 指令：`shasum -a 256 filename.pdf`
- Windows 指令：`certutil -hashfile filename.pdf SHA256`

**4. 收集方法 (Collection Method)**

- 請選擇以下其中一項：

  - 網上下載 (Web download)：從網站下載或自動爬取
  - 網際網路檔案館 (Wayback Machine)：從 Internet Archive/Wayback Machine 取得
  - 政府/法定機構公佈 (Official/Public Record)：從政府憲報、部門網站或法定機構下載
  - 電郵附件 (Email attachment)：以電郵附件形式接收
  - 通訊平台 (Messaging platform)：從通訊平台取得（Telegram, WhatsApp 等）
  - 實體掃描 (Scan of Original/CTC)：從實體正本或核證副本 (Certified True Copy) 掃描
  - 螢幕截圖 (Screen Capture)：網頁/螢幕截圖（僅在無法下載原始檔時使用）
  - 第三方檔案庫 (Third-party archive)：從第三方檔案服務取得
  - 其他 (Other)：其他方法（請在備註中說明）

**5. 收集者 (Collector)**（可選）

- 如未提供，則假設為提交該條目的貢獻者

**範例 / Example:**

```markdown
- [2021-10-04](./2021-10-04.pdf) - 2021年10月4日
  - **Original URL**: https://example.com/document.pdf
  - **Collection Time**: 2025-11-27 14:30
  - **Collection Method**: 網上下載 (Web download)
```

## 六、聲明

本存庫只收錄公開及可查證的資料，不包含未經核實的傳聞。本存庫之目的為保存資料、協助研究及提升事件透明度，不作出任何未經證實的指控。

如有補充資料，歡迎提交。

## 七、如何提交 Issue 或 Pull Request

為方便公眾共同完善內容，本存庫歡迎任何形式的補充、修訂與建議。以下為簡單的操作方式。

### 1. 提交 Issue（提出資料、錯誤更正或建議）

如欲補充資料、指出錯誤或提出改善建議，可按照以下步驟：

1. 前往本存庫主頁
2. 點選頂部的 **Issues** 分頁
3. 按 **New Issue**
4. 在標題與內容中清晰說明：
   - 想補充或修正的內容
   - 資料來源連結（如適用）
   - 涉及的檔案或章節
5. 提交後，維護者會審閱並回覆。

Issue 適用於：

- 提供新的新聞連結、影片或文件來源
- 指出資料錯漏
- 建議改善存庫架構或內容
- 提出應加入的新章節主題

---

### 2. 提交 Pull Request（直接提交修改）

如希望自行編輯或新增資料，可透過 Pull Request 提交具體修訂：

1. 在右上角按 **Fork** 複製本存庫至自己的帳戶
2. 在自己的 fork 中進行修改
3. 修改完成後按 **Pull Request**
4. 在說明中列明：
   - 修改的檔案
   - 新增或更改的內容
   - 資料來源（如有）
   - 修訂原因
5. 提交後，維護者會作出審閱及合併。

Pull Request 適用於：

- 新增資料夾或檔案（如新聞、文件、技術分析）
- 修訂 Markdown 內容、排版或分類
- 補充可引用來源的資料
- 新增 timeline 條目、文件摘要或分析

---

如不熟悉 GitHub，可直接於 Issue 中留言，我們亦會協助整理。

# English Version

# 11.26 Tai Po Wang Fuk Court Fire Documentary

This repository aims to collect, organize, and preserve publicly available information related to the Wang Fuk Court fire in Tai Po on 26 November 2025. Materials include news reports, video footage, technical analyses, contractor information, volunteer and community support resources, official statements, and follow-up developments. The objective is to build a public, centralized, and verifiable archive for researchers, media, engineers, and concerned members of the public.

## 1. Purpose

- To record publicly available information related to the incident (videos, news, documents)
- To establish a clear timeline for understanding the development of events
- To compile technical analyses concerning engineering, materials, and safety standards
- To preserve volunteer and community support information provided during the incident
- To consolidate scattered information from sources such as Threads, IG, Telegram, Google Docs, etc.
- To provide verifiable background information for international readers, researchers, and academics

## 2. Incident Overview

On 26 November 2025, a major fire broke out at Wang Fuk Court in Tai Po. The fire spread rapidly from lower floors to upper floors within a very short time, resulting in significant casualties. The incident raised widespread concerns regarding scaffolding materials, flame-retardant standards, maintenance procedures, and regulatory oversight. Large-scale evacuation followed, with volunteers, local businesses, and NGOs providing immediate support including supplies, temporary rest areas, pet care assistance, sanitation items, and other forms of aid.

## 3. Repository Structure

All main content is located in the `content/` directory:

- **`/timeline/` Timeline**: Chronological record of the incident, including the fire outbreak, rescue operations, and aftermath.
- **`/videos/` Videos**: Collection of on-site footage from social media and news sources, with source links.
- **`/news/` News**: Archive of reports from major media outlets, categorized by media and date.
- **`/analysis/` Analysis**: Technical documents and analyses regarding scaffolding safety, material flame retardancy standards, and fire causes.
- **`/support/` Support**: Information on volunteer services, donation of supplies, and community mutual aid.
- **`/photos/` Photos**: On-site photos and related visual records.
- **`/residents/` Residents**: Collection of residents' discussions, mutual aid messages, and voices from various platforms.
- **`/docs/` Documents**:
  - Government departmental replies and public letters
  - Wang Fuk Court Owners' Corporation Management Committee Meeting Minutes (2021-2025, 34 records): [PDF format](content/docs/meeting_minutes/pdf/README.md) | [Markdown format](content/docs/meeting_minutes/markdown/README.md)

## 4. Key Technical and Research Topics

This repository will document and analyze topics including:

- Physical and safety comparisons between bamboo scaffolding and metal scaffolding
- Legal flame-retardant requirements and standards for safety netting in Hong Kong
- Responsibilities and management systems for contractors during maintenance works
- Possible mechanisms leading to the rapid vertical fire spread
- Material ignition points, chimney effects, engineering workflow, and inspection procedures
- Public statements from engineering, material science, and firefighting experts

## 5. Public Contribution

Contributions are welcome from residents, researchers, and professionals:

- Adding new information or sources
- Correcting or updating existing content
- Providing technical or policy analysis
- Consolidating volunteer or community support information
- Submitting Pull Requests or Issues to improve the repository
  - If you are unfamiliar with how GitHub works, we recommend you use Issues to suggest changes

### Information to Include When Submitting Documents

To ensure documents can serve as valid evidence, please include the following information when submitting documents:

**1. Original URL**

- The original source URL of the document
- If the source is no longer available, please note this and provide backup sources (e.g., Wayback Machine)

**2. Collection Time**

- Record when you obtained the document
- Format example: `2025-11-27 14:30` (assume HKT if timezone is not provided)
- If not provided, assumed to be the time when the file was first committed to the repository (original commit time)

**3. File Hash (SHA-256) [Recommended for Evidence]**

- Helps verify file integrity for legal/archival purposes.
- Mac/Linux command: `shasum -a 256 filename.pdf`
- Windows command: `certutil -hashfile filename.pdf SHA256`
- Windows PowerShell command: `Get-FileHash filename.pdf`

**4. Collection Method**

- Please choose one of the following:

  - 網上下載 (Web download): Download or automated scraping from website
  - 網際網路檔案館 (Wayback Machine): Retrieved from Internet Archive/Wayback Machine
  - 政府/法定機構公佈 (Official/Public Record): Downloaded from government gazette, department website, or statutory body
  - 電郵附件 (Email attachment): Received as email attachment
  - 通訊平台 (Messaging platform): Retrieved from messaging platform (Telegram, WhatsApp, etc.)
  - 實體掃描 (Scan of Original/CTC): Scanned from original document or Certified True Copy
  - 螢幕截圖 (Screen Capture): Screenshot of webpage/screen (use only if original file is unavailable)
  - 第三方檔案庫 (Third-party archive): Retrieved from third-party archive service
  - 其他 (Other): Other method (please specify in notes)

**5. Collector** (Optional)

- If not provided, assumed to be the contributor who added this entry

**Example:**

```markdown
- [2021-10-04](./2021-10-04.pdf) - 2021年10月4日
  - **Original URL**: https://example.com/document.pdf
  - **Collection Time**: 2025-11-27 14:30
  - **Collection Method**: 網上下載 (Web download)
```

## 6. Disclaimer

This repository only includes publicly available and verifiable information.
Unverified rumors will not be included.
The purpose of this archive is to preserve information, support research, and improve transparency.
No unverified allegations will be made.

Contributions and additional data are welcome.

## 7. How to Submit an Issue or Pull Request

To facilitate community collaboration, this repository accepts Issues and Pull Requests.
Below are basic instructions.

### 1. Submitting an Issue (new information, corrections, suggestions)

1. Go to the repository main page
2. Click **Issues**
3. Select **New Issue**
4. Provide:
   - Details of the information to add or correct
   - Source links (if applicable)
   - Relevant files or sections
5. Submit the issue for review

Issues are suitable for:

- Adding news links, videos, or document sources
- Reporting errors or omissions
- Suggesting improvements to structure and content
- Proposing new topics for inclusion

---

### 2. Submitting a Pull Request (direct edits)

1. Click **Fork** to create a copy of the repository
2. Make edits in your own branch
3. Click **Pull Request**
4. Provide a summary including:
   - Modified files
   - Description of changes
   - Source references (if applicable)
   - Reason for the revision
5. Maintainers will review and merge if appropriate

Pull Requests are suitable for:

- Adding folders or files (e.g., news, documents, analysis)
- Improving Markdown structures or formatting
- Adding verified data
- Updating timelines, summaries, and technical analysis

---

If you are unfamiliar with GitHub, you may also leave a comment in Issues and maintainers will assist with formatting and integration.
