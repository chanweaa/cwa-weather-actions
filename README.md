# CWA 氣溫資料自動抓取 (GitHub Actions)

用 GitHub Actions 每 2 小時抓一次中央氣象署（CWA）開放資料，篩選出：

- 新北市**汐止區**
- 基隆市**七堵區**
- 基隆市**五堵**（地名，行政上屬七堵區，用測站/地名關鍵字比對）

資料**只新增、不刪除**，每週累積寫在同一個檔案裡；每逢**星期日**會自動另外開一個新檔案，
之前的資料完整保留，不會被覆寫或清除。

## 檔案結構

```
.github/workflows/fetch-weather.yml   # 排程設定 (cron，每 2 小時)
scripts/fetch_weather.py              # 抓資料 + 篩選地區 + 累積寫入 .md 的腳本
data/weather-week-YYYY-MM-DD.md       # 週記錄檔，檔名是「那一週星期日」的日期，只增不刪
data/latest.md                        # 每次執行後覆寫的最新一筆資料（快速查看用）
```

### 週記錄檔的運作方式

- 檔名用「這一週星期日的日期」命名，例如 `weather-week-2026-09-06.md` 代表
  9/6（日）到 9/12（六）這一週的所有記錄。
- 每次排程執行（每 2 小時一次）就在該檔案**尾端新增**一個時間區塊的表格，
  不會刪除或覆寫先前寫入的內容。
- 到了下一個星期日，日期算出來的檔名會自動變成新的一個，等於自動開新檔，
  舊的一週檔案就保留下來不再變動。

## 設定步驟

### 1. 申請 CWA 開放資料授權碼

到 [中央氣象署開放資料平台](https://opendata.cwa.gov.tw/) 註冊會員 → 「會員專區」→「取得授權碼」，
會拿到一組類似 `CWA-XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX` 的 Authorization Key。

### 2. 把 API Key 存到 GitHub Secrets

到你的 repo → **Settings → Secrets and variables → Actions → New repository secret**：
- Name: `CWA_API_KEY`
- Value: 貼上剛剛拿到的授權碼

**絕對不要**把 API Key 直接寫在程式碼或 workflow 檔裡。

### 3. 設定 Gmail 寄信用的 Secrets

腳本抓完資料、commit 完之後，會自動把結果寄一封信到指定的 Gmail 信箱
（信件內容是這次抓到的最新資料，並附加當週的完整記錄檔）。

Gmail 不能直接用登入密碼給第三方程式使用，需要先開「應用程式密碼」：

1. 到你的 Google 帳戶 → **安全性** → 開啟「兩步驟驗證」（沒開的話要先開）。
2. 開啟後，在同一個「安全性」頁面搜尋 **應用程式密碼 (App Passwords)**，
   建立一組新的應用程式密碼（名稱隨意，例如 "GitHub Actions"），
   會產生一組 16 碼的密碼，**這組密碼只會顯示一次，要先複製起來**。

接著到你的 repo → **Settings → Secrets and variables → Actions → New repository secret**，
新增以下三個 Secret：

| Secret 名稱 | 內容 |
|---|---|
| `GMAIL_USERNAME` | 你的 Gmail 完整地址，例如 `example@gmail.com` |
| `GMAIL_APP_PASSWORD` | 剛剛產生的 16 碼應用程式密碼（不是你的 Gmail 登入密碼） |
| `MAIL_TO` | 要收信的信箱地址（可以跟 `GMAIL_USERNAME` 相同，寄給自己） |

> 應用程式密碼一旦弄丟只能重新產生一組，不用擔心洩漏 Gmail 本身的登入密碼——
> 應用程式密碼可以隨時到 Google 帳戶頁面單獨撤銷，不影響帳號本身。

### 4. 確認 Actions 有寫入權限

到 repo → **Settings → Actions → General → Workflow permissions**，選擇
「**Read and write permissions**」，這樣 Action 才能把更新後的 `.md` commit 回 repo。

### 5. 調整想抓的地區（若需要）

`.github/workflows/fetch-weather.yml` 裡有兩個環境變數：

```yaml
env:
  CWA_API_KEY: ${{ secrets.CWA_API_KEY }}
  COUNTIES: "新北市,基隆市"        # 要查詢的縣市（CWA API 只能用縣市查）
  LOCATION_KEYWORDS: "汐止,七堵,五堵"  # 用來比對鄉鎮/測站名稱的關鍵字
```

腳本會先用 `COUNTIES` 把該縣市**所有測站**抓回來，再用 `LOCATION_KEYWORDS`
在鄉鎮名稱或測站名稱裡比對關鍵字，篩出真正要的測站。如果之後想加/改地區，
改這兩個變數即可，不用動程式碼。

> 提醒：「五堵」不是正式行政區名稱（正式行政區是基隆市七堵區），
> CWA 資料裡是以**測站名稱**（例如「五堵」測站）出現，所以用關鍵字比對而非
> 嚴格比對行政區全名，才抓得到。

### 6. 排程頻率

目前設定為**每 2 小時一次**：

```yaml
- cron: "5 */2 * * *"
```

對應台灣時間約 00:05 / 02:05 / 04:05 / 06:05 / 08:05 / 10:05 / 12:05 / 14:05 / 16:05 / 18:05 / 20:05 / 22:05（每 2 小時一次，一天共 12 次）。若要調整：

| 想要的頻率 | cron 寫法 |
|---|---|
| 每 1 小時 | `5 * * * *` |
| 每 3 小時 | `5 */3 * * *` |
| 每 6 小時 | `5 */6 * * *` |
| 每天一次（台灣時間 08:05） | `5 0 * * *` |

> 注意：GitHub Actions 的排程時間常有幾分鐘延遲，不保證準點觸發，
> 尤其是免費方案的 repo。

### 7. 手動測試

Push 上去之後，到 repo 的 **Actions** 分頁，選 "Fetch CWA Weather Data" →
右上角 **Run workflow** 可以立即手動觸發一次，確認：
- `data/` 底下有正確產生/更新檔案
- 指定的 Gmail 信箱有收到信（記得檢查垃圾郵件匣，第一次寄信偶爾會被歸類進去）

## 資料來源

使用 CWA API：**O-A0003-001（現在天氣觀測報告資料 - 自動氣象站）**。
官方 API 文件：https://opendata.cwa.gov.tw/dist/opendata-swagger.html
