#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
從中央氣象署（CWA）開放資料平台抓取「現在天氣觀測報告」資料，
篩選出指定地區（預設：新北市汐止區、基隆市七堵區、基隆市五堵）的氣溫，
以「只新增、不刪除」的方式累積寫入同一份週記錄檔，每週日自動另開新檔。

需要的環境變數：
  CWA_API_KEY        必填，CWA 開放資料平台的授權碼 (Authorization Key)
  COUNTIES           選填，逗號分隔的縣市清單，預設 "新北市,基隆市"
  LOCATION_KEYWORDS  選填，逗號分隔的地區關鍵字（比對鄉鎮或測站名稱），
                      預設 "汐止,七堵,五堵"

資料來源 API：O-A0003-001（現在天氣觀測報告-自動氣象站）
文件：https://opendata.cwa.gov.tw/dist/opendata-swagger.html

注意：CWA API 只能用「縣市」或「測站名稱」查詢，不能直接用「鄉鎮」查詢，
所以這裡的做法是：先用縣市抓回該縣市全部測站，再用關鍵字在本地端比對
鄉鎮名稱 (TownName) 或測站名稱 (StationName) 來篩選。
"五堵"並非正式行政區名（屬基隆市七堵區），故用「測站/地名關鍵字」比對，
而不是嚴格比對行政區全名，這樣才抓得到「五堵」測站。
"""

import os
import sys
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
import urllib.request
import urllib.parse

API_URL = "https://opendata.cwa.gov.tw/api/v1/rest/datastore/O-A0003-001"
TAIPEI_TZ = timezone(timedelta(hours=8))
DATA_DIR = Path(__file__).resolve().parent.parent / "data"

DEFAULT_COUNTIES = ["新北市", "基隆市"]
DEFAULT_KEYWORDS = ["汐止", "七堵", "五堵"]


def fetch_data_for_county(api_key: str, county: str) -> dict:
    params = {
        "Authorization": api_key,
        "format": "JSON",
        "CountyName": county,
    }
    url = f"{API_URL}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"User-Agent": "github-actions-weather-bot"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        raw = resp.read().decode("utf-8")
    return json.loads(raw)


def parse_stations(payload: dict) -> list[dict]:
    """把 CWA 回傳的 JSON 整理成簡單好用的 list[dict]。"""
    stations_raw = payload.get("records", {}).get("Station", [])
    result = []
    for s in stations_raw:
        try:
            name = s.get("StationName", "未知測站")
            station_id = s.get("StationId", "")
            county = s.get("GeoInfo", {}).get("CountyName", "")
            town = s.get("GeoInfo", {}).get("TownName", "")
            obs_time = s.get("ObsTime", {}).get("DateTime", "")
            temp = s.get("WeatherElement", {}).get("AirTemperature", None)
            humidity = s.get("WeatherElement", {}).get("RelativeHumidity", None)
            weather = s.get("WeatherElement", {}).get("Weather", "")

            # CWA 用 -99 代表無資料
            if temp in (None, -99, -99.0):
                continue

            result.append({
                "station_id": station_id,
                "name": name,
                "county": county,
                "town": town,
                "obs_time": obs_time,
                "temperature": temp,
                "humidity": humidity,
                "weather": weather,
            })
        except Exception:
            continue
    return result


def filter_by_keywords(stations: list[dict], keywords: list[str]) -> list[dict]:
    """比對鄉鎮名稱或測站名稱是否包含任一關鍵字。"""
    matched = []
    for s in stations:
        haystack = f"{s['town']} {s['name']}"
        if any(kw in haystack for kw in keywords):
            matched.append(s)
    return matched


def week_start_sunday(d: datetime) -> str:
    """回傳這一天所屬那一週的「星期日」日期字串 (YYYY-MM-DD)。
    ISO weekday: 星期一=1 ... 星期日=7。
    """
    iso_wd = d.isoweekday()
    days_since_sunday = 0 if iso_wd == 7 else iso_wd
    sunday = d.date() - timedelta(days=days_since_sunday)
    return sunday.isoformat()


def render_run_block(stations: list[dict], fetched_at: datetime) -> str:
    lines = []
    lines.append(f"## {fetched_at.strftime('%Y-%m-%d %H:%M:%S')} (UTC+8)")
    lines.append("")
    if not stations:
        lines.append("_本次未抓到符合條件的測站資料。_")
        lines.append("")
        return "\n".join(lines)

    lines.append("| 測站 | 縣市 | 鄉鎮 | 觀測時間 | 氣溫(°C) | 濕度 | 天氣 |")
    lines.append("|---|---|---|---|---|---|---|")
    for s in sorted(stations, key=lambda x: (x["county"], x["town"], x["name"])):
        lines.append(
            f"| {s['name']} | {s['county']} | {s['town']} | {s['obs_time']} "
            f"| {s['temperature']} | {s['humidity']} | {s['weather']} |"
        )
    lines.append("")
    return "\n".join(lines)


def render_latest(stations: list[dict], fetched_at: datetime) -> str:
    lines = []
    lines.append("# 最新氣溫（汐止 / 七堵 / 五堵）")
    lines.append("")
    lines.append(f"更新時間：{fetched_at.strftime('%Y-%m-%d %H:%M:%S')} (UTC+8)")
    lines.append("")
    if not stations:
        lines.append("_目前沒有符合條件的測站資料。_")
        return "\n".join(lines) + "\n"

    lines.append("| 測站 | 縣市 | 鄉鎮 | 觀測時間 | 氣溫(°C) | 濕度 | 天氣 |")
    lines.append("|---|---|---|---|---|---|---|")
    for s in sorted(stations, key=lambda x: (x["county"], x["town"], x["name"])):
        lines.append(
            f"| {s['name']} | {s['county']} | {s['town']} | {s['obs_time']} "
            f"| {s['temperature']} | {s['humidity']} | {s['weather']} |"
        )
    lines.append("")
    return "\n".join(lines)


def main():
    api_key = os.environ.get("CWA_API_KEY")
    if not api_key:
        print("錯誤：找不到環境變數 CWA_API_KEY", file=sys.stderr)
        sys.exit(1)

    counties_env = os.environ.get("COUNTIES")
    counties = [c.strip() for c in counties_env.split(",")] if counties_env else DEFAULT_COUNTIES

    keywords_env = os.environ.get("LOCATION_KEYWORDS")
    keywords = [k.strip() for k in keywords_env.split(",")] if keywords_env else DEFAULT_KEYWORDS

    all_stations = []
    for county in counties:
        payload = fetch_data_for_county(api_key, county)
        all_stations.extend(parse_stations(payload))

    matched = filter_by_keywords(all_stations, keywords)

    # 依 station_id 去重（避免同一測站因縣市抓取重疊而重複出現）
    dedup = {}
    for s in matched:
        dedup[s["station_id"] or s["name"]] = s
    matched = list(dedup.values())

    if not matched:
        print("警告：本次沒有抓到符合關鍵字的測站資料，仍會記錄一筆空結果。", file=sys.stderr)

    now = datetime.now(TAIPEI_TZ)
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    # 1) 週記錄檔：只新增、不刪除。檔名依「這一週的星期日日期」決定，
    #    每週日該日期會變成新的一週 → 自動另開新檔，之前的檔案完整保留。
    week_file = DATA_DIR / f"weather-week-{week_start_sunday(now)}.md"

    is_new_file = not week_file.exists()
    with week_file.open("a", encoding="utf-8") as f:
        if is_new_file:
            f.write(f"# 氣溫記錄（{week_start_sunday(now)} 那一週）\n\n")
            f.write("地區：新北市汐止區、基隆市七堵區、基隆市五堵\n\n")
            f.write("> 本檔案採「只新增、不刪除」方式記錄，每週日會自動另開一個新檔。\n\n")
        f.write(render_run_block(matched, now))
        f.write("\n")

    # 2) latest.md：永遠是最新一次抓取結果，方便快速查看目前狀況（會被覆寫）
    latest_path = DATA_DIR / "latest.md"
    latest_path.write_text(render_latest(matched, now), encoding="utf-8")

    print(f"已寫入 {week_file}（新增 {len(matched)} 筆）與 {latest_path}。")

    # 把檔案路徑輸出給 GitHub Actions 後續步驟使用（例如寄信步驟要附加檔案）
    github_output = os.environ.get("GITHUB_OUTPUT")
    if github_output:
        with open(github_output, "a", encoding="utf-8") as f:
            f.write(f"week_file={week_file}\n")
            f.write(f"latest_file={latest_path}\n")
            f.write(f"station_count={len(matched)}\n")


if __name__ == "__main__":
    main()
