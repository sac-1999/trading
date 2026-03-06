
from flask import Flask, jsonify, request
from datetime import datetime

app = Flask(__name__)

# --- Dummy in-memory data (you can replace this anytime) ---
STOCKS = [
    {"symbol": "RELIANCE", "name": "Reliance Industries", "price": 2548.35, "change_pct": 1.42, "volume": 3_421_000},
    {"symbol": "TCS",      "name": "Tata Consultancy Services", "price": 4210.50, "change_pct": -0.38, "volume": 1_105_420},
    {"symbol": "INFY",     "name": "Infosys", "price": 1536.90, "change_pct": 2.18, "volume": 2_045_100},
    {"symbol": "HDFCBANK", "name": "HDFC Bank", "price": 1712.25, "change_pct": -1.05, "volume": 4_010_300},
    {"symbol": "SBIN",     "name": "State Bank of India", "price": 662.40, "change_pct": 0.74, "volume": 5_221_900},
    {"symbol": "ITC",      "name": "ITC", "price": 452.10, "change_pct": -0.12, "volume": 2_311_750},
    {"symbol": "LT",       "name": "Larsen & Toubro", "price": 3689.00, "change_pct": 3.45, "volume": 980_210},
    {"symbol": "BHARTIARTL","name": "Bharti Airtel", "price": 1362.75, "change_pct": 0.15, "volume": 1_554_330},
    {"symbol": "ASIANPAINT","name": "Asian Paints", "price": 2995.20, "change_pct": -2.61, "volume": 745_880},
    {"symbol": "MARUTI",  "name": "Maruti Suzuki", "price": 10950.00, "change_pct": 0.98, "volume": 312_420},
]

def _apply_filters(items, min_change=None, max_change=None, symbols=None):
    out = items
    if min_change is not None:
        out = [s for s in out if s["change_pct"] >= min_change]
    if max_change is not None:
        out = [s for s in out if s["change_pct"] <= max_change]
    if symbols:
        wanted = set(sym.upper() for sym in symbols)
        out = [s for s in out if s["symbol"].upper() in wanted]
    return out

def _sort_items(items, sort_key="symbol", order="asc"):
    reverse = order.lower() == "desc"
    # supported sort keys: symbol, name, price, change_pct, volume
    key = sort_key if sort_key in {"symbol", "name", "price", "change_pct", "volume"} else "symbol"
    return sorted(items, key=lambda s: s[key], reverse=reverse)

def _paginate(items, limit=None):
    if limit is None:
        return items
    try:
        limit = int(limit)
    except Exception:
        return items
    return items[:max(0, limit)]

def _meta():
    return {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "count": len(STOCKS),
        "source": "dummy",
    }

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "time": datetime.utcnow().isoformat() + "Z"})

@app.route("/stocks", methods=["GET"])
def list_stocks():
    """
    Query params:
      - sort: symbol|name|price|change_pct|volume (default: symbol)
      - order: asc|desc (default: asc)
      - min_change: float (filter by minimum % change)
      - max_change: float (filter by maximum % change)
      - symbols: comma-separated symbols (e.g., RELIANCE,TCS)
      - limit: int (max results)
    """
    sort_key = request.args.get("sort", "symbol")
    order = request.args.get("order", "asc")

    min_change = request.args.get("min_change")
    max_change = request.args.get("max_change")
    symbols = request.args.get("symbols")
    limit = request.args.get("limit")

    min_change = float(min_change) if min_change is not None else None
    max_change = float(max_change) if max_change is not None else None
    symbols = [s.strip() for s in symbols.split(",")] if symbols else None

    items = _apply_filters(STOCKS, min_change, max_change, symbols)
    items = _sort_items(items, sort_key, order)
    items = _paginate(items, limit)

    return jsonify({
        "meta": _meta(),
        "data": items
    })

@app.route("/stocks/top-gainers", methods=["GET"])
def top_gainers():
    """Top N gainers by change_pct (default N=5). ?limit=10 to customize."""
    limit = request.args.get("limit", 5)
    try:
        limit = int(limit)
    except Exception:
        limit = 5
    items = [s for s in STOCKS if s["change_pct"] >= 0.0]
    items = sorted(items, key=lambda s: s["change_pct"], reverse=True)
    items = items[:limit]
    return jsonify({"meta": _meta(), "data": items})

@app.route("/stocks/top-losers", methods=["GET"])
def top_losers():
    """Top N losers by change_pct (default N=5). ?limit=10 to customize."""
    limit = request.args.get("limit", 5)
    try:
        limit = int(limit)
    except Exception:
        limit = 5
    items = [s for s in STOCKS if s["change_pct"] < 0.0]
    items = sorted(items, key=lambda s: s["change_pct"])  # ascending (more negative first)
    items = items[:limit]
    return jsonify({"meta": _meta(), "data": items})

if __name__ == "__main__":
    # Run in development mode
    app.run(host="0.0.0.0", port=5000, debug=True)
