
import PoisitiveTradingCard from "./positivetradingcard.jsx";
import NegativeTradingCard from "./negativetradingcard.jsx";
import IndicesTradingCard from "./indicesTradingCard.jsx"
import React, { useEffect, useMemo, useRef, useState } from "react";

const DEFAULT_STREAM_URL = "http://127.0.0.1:5000/stream";

function safeJSON(text) {
  try {
    return JSON.parse(text);
  } catch {
    return null;
  }
}

function toNum(v) {
  const n = typeof v === "number" ? v : parseFloat(v);
  return Number.isFinite(n) ? n : 0;
}

function SymbolCard() {
  const [gainers, setGainers] = useState({}); // { [symbol]: stockObj }
  const [losers, setLosers] = useState({});   // { [symbol]: stockObj }
  const [indices, setIndices] = useState({});  
  const [status, setStatus] = useState("connecting");
  const logsRef = useRef(null);
  const esRef = useRef(null);

  const streamUrl = useMemo(() => DEFAULT_STREAM_URL, []);

  useEffect(() => {
    const es = new EventSource(streamUrl, { withCredentials: false });
    esRef.current = es;
    es.onopen = () => setStatus("connected");
    es.onerror = () => setStatus("error");

    const handlePayload = (type, raw) => {
      const obj = safeJSON(raw);
      if (!obj) return;

      const symbol = obj.symbol || "unknown";
      const change = toNum(obj?.curr_day_state?.change);
      console.log(symbol)
      if (symbol.endsWith("_index"))
      {

         setIndices((prev) => ({
          ...prev,
          [symbol]: obj,
        }));
      }

      else if (change > 0) {
        setGainers((prev) => ({
          ...prev,
          [symbol]: obj,
        }));
      } else {
        setLosers((prev) => ({
          ...prev,
          [symbol]: obj,
        }));
      }
    };

    es.onmessage = (e) => handlePayload("message", e.data);
    es.addEventListener("update", (e) => handlePayload("update", e.data));

    return () => {
      try {
        es.close();
      } catch {}
      esRef.current = null;
    };
  }, [streamUrl]);

  /** ---------- Derived, sorted arrays ---------- */
  const sortedGainers = useMemo(() => {
    // Biggest positive change first
    return Object.values(gainers)
      .slice()
      .sort((a, b) => {
        const ca = toNum(a?.curr_day_state?.change);
        const cb = toNum(b?.curr_day_state?.change);
        if (cb !== ca) return cb - ca; // descending by change
        // Tie-breaker: optional, by symbol or last close
        return String(a.symbol).localeCompare(String(b.symbol));
      });
  }, [gainers]);

  const sortedLosers = useMemo(() => {
    // Most negative change first
    return Object.values(losers)
      .slice()
      .sort((a, b) => {
        const ca = toNum(a?.curr_day_state?.change);
        const cb = toNum(b?.curr_day_state?.change);
        if (ca !== cb) return ca - cb; // ascending: -7, -6, ...
        return String(a.symbol).localeCompare(String(b.symbol));
      });
  }, [losers]);


  const sortedindices = useMemo(() => {
    return Object.values(indices)
      .slice()
      .sort((a, b) => {
        const ca = toNum(a?.curr_day_state?.change);
        const cb = toNum(b?.curr_day_state?.change);
        if (ca !== cb) return cb - ca; // ascending: -7, -6, ...
        return String(a.symbol).localeCompare(String(b.symbol));
      });
  }, [indices]);

  return (
    <>
      <section className="w-full px-4">
        <div className="flex flex-row p-5">
          {/* Gainers */}
          <div className="w-1/2 flex flex-col p-5">
            {sortedGainers.length === 0 ? (
              <div className="text-slate-400">No positive movers yet…</div>
            ) : (
              sortedGainers.map((stock) => (
                <PoisitiveTradingCard key={stock.symbol} stockData={stock} />
              ))
            )}
          </div>

          {/* Losers */}
          <div className="w-1/2 flex flex-col p-5">
            {sortedLosers.length === 0 ? (
              <div className="text-slate-400">No negative movers yet…</div>
            ) : (
              sortedLosers.map((stock) => (
                <NegativeTradingCard key={stock.symbol} stockData={stock} />
              ))
            )}
          </div>

           {/* Indices */}
          <div className="w-1/2 flex flex-col p-5">
            {sortedindices.length === 0 ? (
              <div className="text-slate-400">No Indices data yet…</div>
            ) : (
              sortedindices.map((stock) => (
                <IndicesTradingCard key={stock.symbol} stockData={stock} />
              ))
            )}
          </div>

          
        </div>
      </section>
    </>
  );
}

export default SymbolCard;
