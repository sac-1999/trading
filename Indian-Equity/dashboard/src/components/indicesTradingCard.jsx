
import React, { useState } from 'react';
import { Activity } from 'lucide-react';

const IndicesTradingCard = ({ stockData }) => {
  console.log(stockData);

  /**
   * Map change (%) in [-3, 3] to [0, 100]
   * -3%  -> 0%
   *  0%  -> 50%
   * +3%  -> 100%
   */
  const getPosition = (percentage) => {
    const clamped = Math.max(-1, Math.min(1, Number(percentage) || 0));
    return ((clamped + 3) / 6) * 100;
  };

  // Clamp helper to keep positions in [0..100]
  const clampPercent = (p) => Math.max(0, Math.min(100, p));

  // Calculate positions relative to last close (% change from last close to price level)
  const getRelativePosition = (level) => {
    const base = Number(stockData.last_day_state?.close) || 0;
    if (!base) return 50; // fallback to center if base is invalid
    const percentDiff = ((Number(level) - base) / base) * 100;
    return clampPercent(getPosition(percentDiff));
  };

  // Given two prices, compute { left%, width% } on the bar (same pattern as your sample)
  const segmentFromPrices = (a, b) => {
    const pa = getRelativePosition(a);
    const pb = getRelativePosition(b);
    const left = Math.min(pa, pb);
    const width = Math.abs(pb - pa);
    return { left, width };
  };

  const dailyPosition = getPosition(stockData.curr_day_state?.change);

  // Extract prices (same as your sample expectation)
  const { open, close, high } = stockData.curr_day_state || {};

  // Segments (exactly like your sample)
  const oc = segmentFromPrices(open, close); // Black: Open ↔ Close
  const ho = segmentFromPrices(high, open);  // Grey: High ↔ Open (above)
  const hc = segmentFromPrices(high, close); // Grey: High ↔ Close (below)

  // Baseline Y (same as your sample’s top-5 ≈ 20px inside the container)
  const baselineTopPx = '20px';

  return (
    <div className="bg-white">
      <div className="w-full">
        {/* Main Card */}
        <div className="bg-white rounded border border-gray-200">
          {/* Daily Change Scale Bar */}
          <div>
            <div className="relative">
              <div className="relative bg-gray-50 rounded p-1 border border-gray-100">
                {/* Stock Name - Absolute Position (unchanged) */}
                <div className="absolute top-1 left-2 z-20">
                  <span className="text-[10px] font-bold text-gray-700 bg-white/80 px-1 rounded">
                    {stockData.symbol}
                  </span>
                </div>

                {/* Keep your original height */}
                <div className="relative h-5">
                  {/* Gradient Background (unchanged colors) */}
                  <div className="absolute inset-x-0 top-3 h-6 rounded overflow-hidden">
                    <div className="absolute inset-0 bg-gradient-to-r from-red-100 via-red-50 to-yellow-50"></div>
                  </div>

                  {/* ===================== Horizontal segments (from your sample) ===================== */}
                  <>
                    {/* Open ↔ Close (sharp thin black, 1px) */}
                    {oc.width > 0.5 ? (
                      <div
                        className="absolute h-px bg-black"
                        style={{
                          top: baselineTopPx,
                          left: `${oc.left}%`,
                          width: `${oc.width}%`,
                          transform: 'translateY(-0.5px)', // crisp subpixel alignment
                          zIndex: 10,
                        }}
                        title={`Open↔Close: ${open} ↔ ${close}`}
                      />
                    ) : (
                      // If open==close (width ~0), show a dot
                      <div
                        className="absolute w-[6px] h-[6px] bg-black rounded-full"
                        style={{
                          top: baselineTopPx,
                          left: `calc(${oc.left}% - 3px)`,
                          transform: 'translateY(-50%)',
                          zIndex: 10,
                        }}
                        title={`Open=Close: ${open}`}
                      />
                    )}

                    {/* High ↔ Open (light grey, 2px) — 1px above baseline */}
                    {ho.width > 0.5 && (
                      <div
                        className="absolute h-[2px] bg-gray-300 rounded"
                        style={{
                          top: `calc(${baselineTopPx} - 1px)`,
                          left: `${ho.left}%`,
                          width: `${ho.width}%`,
                          zIndex: 9,
                        }}
                        title={`High↔Open: ${high} ↔ ${open}`}
                      />
                    )}

                    {/* High ↔ Close (light grey, 2px) — 1px below baseline */}
                    {hc.width > 0.5 && (
                      <div
                        className="absolute h-[2px] bg-gray-300 rounded"
                        style={{
                          top: `calc(${baselineTopPx} + 1px)`,
                          left: `${hc.left}%`,
                          width: `${hc.width}%`,
                          zIndex: 9,
                        }}
                        title={`High↔Close: ${high} ↔ ${close}`}
                      />
                    )}
                  </>

                  {/* Current position indicator (unchanged) */}
                  <div
                    className="absolute top-4 h-8 transition-all duration-700 ease-out"
                    style={{ left: `${dailyPosition}%` }}
                  >
                    <div className="relative flex flex-col items-center -translate-x-1/2">
                      {/* Value label (kept styling/colors) */}
                      <div className="absolute -top-5 bg-red-500 text-white px-1 py-0.5 rounded text-[9px] font-bold whitespace-nowrap shadow-sm">
                        <div className="absolute bottom-0 left-1/2 transform -translate-x-1/2 translate-y-1/2 rotate-45 w-1 h-1 bg-red-500"></div>
                        {stockData.curr_day_state?.change}
                      </div>
                    </div>
                  </div>
                </div>

                {/* Scale markers: -3 .. +3 (unchanged) */}
                <div className="relative flex justify-between text-[9px] font-medium text-gray-600">
                  <span className="text-red-900">-3</span>
                  <span className="text-red-800">-2.5</span>
                  <span className="text-red-700">-2</span>
                  <span className="text-red-600">-1.5</span>
                  <span className="text-red-500">-1</span>
                  <span className="text-red-400">-0.5</span>
                  <span className="text-gray-700 font-bold">0</span>
                  <span className="text-green-300">+0.5</span>
                  <span className="text-green-400">+1</span>
                  <span className="text-green-500">+1.5</span>
                  <span className="text-green-600">+2</span>
                  <span className="text-green-700">+2.5</span>
                  <span className="text-green-800">+3</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div> 
    </div>
  );
};

export default IndicesTradingCard;
