
import React, { useEffect, useMemo, useRef, useState } from "react";

const DEFAULT_STREAM_URL = "http://127.0.0.1:5000/stream";

function getQueryParam(name) {
  if (typeof window === "undefined") return null;
  const u = new URL(window.location.href);
  return u.searchParams.get(name);
}

function safeJSON(text) {
  try {
    return JSON.parse(text);
  } catch {
    return null;
  }
}

function formatPayload(obj) {
  const sym = obj?.symbol ?? "unknown";
  const ts = obj?.ts ?? null;

  // last_day_state: { open, high, low, close }
  const s = obj?.last_day_state;
  let summary = s ? `O:${s.open} H:${s.high} L:${s.low} C:${s.close}` : "";

  // curr_day_state: [open, low, close, high, change%]
  const c = obj?.curr_day_state;
  if (!summary && Array.isArray(c) && c.length >= 5) {
    summary = `O:${c[0]} L:${c[1]} C:${c[2]} H:${c[3]} Δ%:${c[4]}`;
  }
  return { sym, ts, summary };
}

export default function LiveStream({ url, initialFilter }) {
  const streamUrl = useMemo(
    () => getQueryParam("url") || url || DEFAULT_STREAM_URL,
    [url]
  );
  const [status, setStatus] = useState("connecting"); 
  const [lines, setLines] = useState([]);
  const logsRef = useRef(null);
  const esRef = useRef(null);

  useEffect(() => {
    const es = new EventSource(streamUrl, { withCredentials: false });
    esRef.current = es;
    es.onopen = () => setStatus("connected");
    es.onerror = () => setStatus("error");

    const pushLine = (type, data) => {
      setLines((prev) => [...prev, `[${type}] ${data}`]);
      requestAnimationFrame(() => {
        const el = logsRef.current;
        if (el) el.scrollTop = el.scrollHeight;
      });
    };

    const handlePayload = (type, raw) => {
      const obj = safeJSON(raw);
      if (!obj) return pushLine(type, raw);

      const symbol = (obj?.symbol ?? "").toString();
      if (filterText && !symbol.toLowerCase().includes(filterText.toLowerCase())) {
        return;
      }

      const { sym, ts, summary } = formatPayload(obj);
      pushLine(type, `${sym} ${summary}${ts ? ` (ts:${ts})` : ""}`);
    };

    // Default messages (no `event:` line)
    es.onmessage = (e) => handlePayload("message", e.data);

    // If server uses `event: update`
    es.addEventListener("update", (e) => handlePayload("update", e.data));

    return () => {
      try { es.close(); } catch {}
      esRef.current = null;
    };
  }, [streamUrl, filterText]);

  const statusText =
    status === "connected"
      ? "Connected"
      : status === "error"
      ? "Disconnected (error). Retrying…"
      : "Connecting…";

  const statusColor =
    status === "connected"
      ? "text-green-400"
      : status === "error"
      ? "text-rose-400"
      : "text-slate-300";

  return (
    <div className="min-h-screen bg-slate-900 text-slate-200">
      {/* Header */}
      <header className="px-4 py-4 border-b border-teal-500/50">
        <h1 className="text-teal-300 text-xl font-semibold">Live Stream</h1>
        <div className={`mt-1 text-sm ${statusColor}`}>{statusText}</div>
        {filterText ? (
          <div className="mt-1 text-xs text-slate-300">
            Filter:{" "}
            <span className="px-2 py-0.5 border border-slate-600 rounded-full">
              {filterText}
            </span>
          </div>
        ) : null}
      </header>

      {/* Logs */}
      <main className="p-4">
        <div
          ref={logsRef}
          aria-live="polite"
          aria-atomic="false"
          className="h-[75vh] overflow-y-auto rounded-md border border-teal-500/50 bg-slate-800 p-3 font-mono whitespace-pre-wrap"
        >
          {lines.length === 0 ? (
            <div className="text-slate-400">Waiting for messages…</div>
          ) : (
            lines.map((line, idx) => (
              <div key={idx} className="mb-1.5">
                <span className="text-teal-300">
                  {line.slice(0, line.indexOf("]") + 1)}
                </span>
                <span className="text-slate-200">
                  {" "}
                  {line.slice(line.indexOf("]") + 1)}
                </span>
              </div>
            ))
          )}
        </div>
      </main>
    </div>
  );
}
