#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
從中央氣象署（CWA）開放資料平台抓取「現在天氣觀測報告」資料，
擷取氣溫並整理成 Markdown 檔案存入 data/ 資料夾。

需要的環境變數：
  CWA_API_KEY  必填，CWA 開放資料平台的授權碼 (Authorization Key)
  COUNTY       選填，縣市名稱過濾（例如 "臺北市"），預設不過濾（全部測站）
  STATION_NAME 選填，測站名稱過濾（例如 "板橋"），預設不過濾

資料來源 API：O-A0003-001（現在天氣觀測報告-自動氣象站）
文件：https://opendata.cwa.gov.tw/dist/opendata-swagger.html
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


def fetch_data(api_key: str, county: str | None, station_name: str | None) -> dict:
    params = {
        "Authorization": api_key,
        "format": "JSON",
    }
    if county:
        params["CountyName"] = county
    if station_name:
        params["StationName"] = station_name

    url = f"{API_URL}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"User-Agent": "github-actions-weather-bot"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        raw = resp.read().decode("utf-8")
    return json.loads(raw)


def parse_stations(payload: dict) -> list[dict]:
    """把 CWA 回傳的 JSON 整理成簡單好用的 list[dict]。"""
    stations_raw = (
        payload.get("records", {})
        .get("Station", [])
    )
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


def render_markdown(stations: list[dict], fetched_at: datetime) -> str:
    lines = []
    lines.append(f"# 中央氣象署氣溫資料")
    lines.append("")
    lines.append(f"更新時間：{fetched_at.strftime('%Y-%m-%d %H:%M:%S')} (UTC+8)")
    lines.append("")
    lines.append("| 測站 | 縣市 | 鄉鎮 | 觀測時間 | 氣溫(°C) | 濕度 | 天氣 |")
    lines.append("|---|---|---|---|---|---|---|")

    stations_sorted = sorted(stations, key=lambda s: (s["county"], s["name"]))
    for s in stations_sorted:
        lines.append(
            f"| {s['name']} | {s['county']} | {s['town']} | {s['obs_time']} "
            f"| {s['temperature']} | {s['humidity']} | {s['weather']} |"
        )

    lines.append("")
    lines.append(f"共 {len(stations_sorted)} 筆測站資料。資料來源：中央氣象署開放資料平台 (CWA Open Data)。")
    lines.append("")
    return "\n".join(lines)


def main():
    api_key = os.environ.get("CWA_API_KEY")
    if not api_key:
        print("錯誤：找不到環境變數 CWA_API_KEY", file=sys.stderr)
        sys.exit(1)

    county = os.environ.get("COUNTY") or None
    station_name = os.environ.get("STATION_NAME") or None

    payload = fetch_data(api_key, county, station_name)
    stations = parse_stations(payload)

    if not stations:
        print("警告：本次沒有抓到任何有效氣溫資料", file=sys.stderr)

    now = datetime.now(TAIPEI_TZ)

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    # 1) 當日快照檔（每天一個檔案，每次執行覆寫最新內容）
    daily_path = DATA_DIR / f"{now.strftime('%Y-%m-%d')}.md"
    daily_path.write_text(render_markdown(stations, now), encoding="utf-8")

    # 2) latest.md：永遠指向最新一次抓取結果，方便直接看
    latest_path = DATA_DIR / "latest.md"
    latest_path.write_text(render_markdown(stations, now), encoding="utf-8")

    print(f"已寫入 {daily_path} 與 {latest_path}，共 {len(stations)} 筆測站資料。")


if __name__ == "__main__":
    main()
