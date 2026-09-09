# CWA 氣溫資料自動抓取 (GitHub Actions)

用 GitHub Actions 定時呼叫中央氣象署（CWA）開放資料 API，把氣溫資料整理成 Markdown 存回這個 repo。

## 檔案結構

```
.github/workflows/fetch-weather.yml   # 排程設定 (cron)
scripts/fetch_weather.py              # 抓資料 + 產生 .md 的腳本
data/latest.md                        # 每次執行後覆寫的最新資料
data/YYYY-MM-DD.md                    # 當天的快照檔
```

## 設定步驟

### 1. 申請 CWA 開放資料授權碼

到 [中央氣象署開放資料平台](https://opendata.cwa.gov.tw/) 註冊會員 → 「會員專區」→「取得授權碼」，
會拿到一組類似 `CWA-XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX` 的 Authorization Key。

### 2. 把 API Key 存到 GitHub Secrets

到你的 repo → **Settings → Secrets and variables → Actions → New repository secret**：
- Name: `CWA_API_KEY`
- Value: 貼上剛剛拿到的授權碼

**絕對不要**把 API Key 直接寫在程式碼或 workflow 檔裡。

### 3. 確認 Actions 有寫入權限

到 repo → **Settings → Actions → General → Workflow permissions**，選擇
「**Read and write permissions**」，這樣 Action 才能把更新後的 `.md` commit 回 repo。

### 4. （選用）篩選特定縣市或測站

預設會抓「全台所有自動氣象站」的資料，檔案會比較大。若只想要特定地區，
編輯 `.github/workflows/fetch-weather.yml`，取消 `COUNTY` 或 `STATION_NAME` 那兩行的註解：

```yaml
env:
  CWA_API_KEY: ${{ secrets.CWA_API_KEY }}
  COUNTY: "臺北市"
  # STATION_NAME: "板橋"
```

### 5. 調整排程頻率

目前設定是**每小時抓一次**（UTC cron `5 * * * *`）。常用調整：

| 想要的頻率 | cron 寫法 |
|---|---|
| 每 10 分鐘 | `*/10 * * * *` |
| 每 6 小時 | `5 */6 * * *` |
| 每天一次（台灣時間 08:05） | `5 0 * * *` |

> 注意：GitHub Actions 的排程時間常會有幾分鐘的延遲，不保證準點觸發，
> 尤其是免費方案的 repo。若時間精準度很重要，考慮改用外部排程器呼叫 `workflow_dispatch`。

### 6. 手動測試

Push 上去之後，到 repo 的 **Actions** 分頁，選 "Fetch CWA Weather Data" →
右上角 **Run workflow** 可以立即手動觸發一次，確認資料抓取正常。

## 資料來源

使用 CWA API：**O-A0003-001（現在天氣觀測報告資料 - 自動氣象站）**。
如果想改抓「未來 36 小時預報」的溫度而不是「即時觀測」，可以把腳本裡的
`API_URL` 換成 `F-C0032-001`，並依該 API 的 JSON 結構調整 `parse_stations()`。

官方 API 文件：https://opendata.cwa.gov.tw/dist/opendata-swagger.html
