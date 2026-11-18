import requests
import json
import os
from datetime import datetime

# ==================== 配置 ====================
KOPYON_KEY = os.environ.get("KOPYON_KEY")
PUSH_TYPE = os.environ.get("PUSH_TYPE", "wecom")  # wecom 或 serverchan
SERVERCHAN_KEY = os.environ.get("SERVERCHAN_KEY", "")
WECOM_WEBHOOK = os.environ.get("WECOM_WEBHOOK", "")

TRADERS = {
    "5075281354358777856": "熬鹰资本",
    # 以后想加其他人，在这里继续加
}

POSITION_FILE = "last_positions.json"
# =============================================

headers = {"X-API-KEY": KOPYON_KEY}

def get_open_positions(trader_id):
    url = f"https://api.kopyon.com/v5/binance-copy-trading/openPositions?traderId={trader_id}"
    r = requests.get(url, headers=headers, timeout=15)
    r.raise_for_status()
    data = r.json().get("data", {})
    positions = data.get("positions", [])
    result = {}
    for p in positions:
        key = f"{p.get('symbol')}_{p.get('side')}"
        result[key] = {
            "symbol": p.get("symbol"),
            "side": p.get("side"),
            "size": float(p.get("size") or p.get("quantity") or 0),
            "entryPrice": p.get("entryPrice") or p.get("avgPrice"),
            "leverage": p.get("leverage"),
        }
    return result

def send_message(title, content):
    if PUSH_TYPE == "serverchan":
        url = f"https://sctapi.ftqq.com/{SERVERCHAN_KEY}.send"
        data = {"title": title, "desp": content}
        requests.post(url, data=data, timeout=10)
    else:
        data = {
            "msgtype": "markdown",
            "markdown": {"content": f"**{title}**\n{content}"}
        }
        requests.post(WECOM_WEBHOOK, json=data, timeout=10)
    print(f"推送成功: {title}")

def load_last():
    if os.path.exists(POSITION_FILE):
        with open(POSITION_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_last(all_positions):
    with open(POSITION_FILE, "w", encoding="utf-8") as f:
        json.dump(all_positions, f, ensure_ascii=False, indent=2)

def compare_and_notify(trader_name, old, new):
    for key, pos in new.items():
        if key not in old:
            title = f"【开仓】{trader_name} | {pos['symbol']} {pos['side']}"
            content = f"币种：{pos['symbol']}\n方向：{pos['side']}\n数量：{pos['size']}\n开仓均价：{pos['entryPrice']}\n杠杆：{pos['leverage']}x\n时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            send_message(title, content)
        elif abs(pos["size"] - old[key]["size"]) > 0.0001:
            change = "加仓" if pos["size"] > old[key]["size"] else "减仓"
            title = f"【{change}】{trader_name} | {pos['symbol']} {pos['side']}"
            content = f"币种：{pos['symbol']}\n方向：{pos['side']}\n原数量：{old[key]['size']} → 现数量：{pos['size']}\n开仓均价：{pos['entryPrice']}\n时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            send_message(title, content)

    for key, pos in old.items():
        if key not in new:
            title = f"【平仓】{trader_name} | {pos['symbol']} {pos['side']}"
            content = f"币种：{pos['symbol']}\n方向：{pos['side']}\n原数量：{pos['size']}\n开仓均价：{pos['entryPrice']}\n时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            send_message(title, content)

def main():
    print("开始检查...")
    all_current = {}
    last_all = load_last()

    for trader_id, trader_name in TRADERS.items():
        current = get_open_positions(trader_id)
        all_current[trader_id] = current
        old = last_all.get(trader_id, {})
        if old:
            compare_and_notify(trader_name, old, current)
        print(f"{trader_name} 当前持仓数: {len(current)}")

    save_last(all_current)
    print("检查完成")

if __name__ == "__main__":
    main()
