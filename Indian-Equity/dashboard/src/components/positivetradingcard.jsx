
import React from 'react';
import { Activity } from 'lucide-react';

const PoisitiveTradingCard = ({ stockData }) => {
  const isPositive = (value) => value >= 0;

  // Calculate position on 0 to 7 scale (percentage)
  const getPosition = (percentage) => {
    const clamped = Math.max(0, Math.min(7, percentage));
    return (clamped / 7) * 100;
  };

  // Clamp helper to defend against out-of-range mapping
  const clampPercent = (p) => Math.max(0, Math.min(100, p));

  // Calculate resistance positions relative to last close (% change from last close to level)
  const getRelativePosition = (level) => {
    const percentDiff = ((level - stockData.last_day_state.close) / stockData.last_day_state.close) * 100;
    return clampPercent(getPosition(percentDiff));
  };

  // Helper: segment left% and width% between two prices
  const segmentFromPrices = (a, b) => {
    const pa = getRelativePosition(a);
    const pb = getRelativePosition(b);
    const left = Math.min(pa, pb);
    const width = Math.abs(pb - pa);
    return { left, width };
  };

  const dailyPosition = getPosition(stockData.curr_day_state.change);

  // Extract prices
  const { open, close, high } = stockData.curr_day_state;

  // Segments
  const oc = segmentFromPrices(open, close); // Dark black: Open ↔ Close
  const ho = segmentFromPrices(high, open);  // Light grey: High ↔ Open
  const hc = segmentFromPrices(high, close); // Light grey: High ↔ Close

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
                <div className="relative h-6">
                  {/* Gradient Background (unchanged) */}
                  <div className="absolute inset-x-0 top-3 h-6 rounded overflow-hidden">
                    <div className="absolute inset-0 bg-gradient-to-r from-yellow-50 via-green-50 to-green-100"></div>
                  </div>

                  {/* ===================== Horizontal segments ===================== */}
                  {/* Use one vertical baseline: align grey to the same baseline as black */}
                  {(() => {
                    // baseline Y (matches your previous black line at top-5)
                    const baselineTopPx = '20px'; // equivalent to top-5 inside this container
                    return (
                      <>
                        {/* Open ↔ Close (sharp thin black, 1px) */}
                        {oc.width > 0.5 ? (
                          <div
                            className="absolute h-px bg-black"
                            style={{
                              top: baselineTopPx,
                              left: `${oc.left}%`,
                              width: `${oc.width}%`,
                              // slight subpixel nudge for crispness
                              transform: 'translateY(-0.5px)',
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

                        {/* High ↔ Open (light grey, 2px) — aligned to overlap, 1px above */}
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

                        {/* High ↔ Close (light grey, 2px) — aligned to overlap, 1px below */}
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
                    );
                  })()}

                  {/* Optional: endpoints for visual clarity (unchanged colors/positions) */}
                  {[open, close].map((p, i) => {
                    const pos = getRelativePosition(p);
                    return (
                      <div
                        key={`endpoint-oc-${i}`}
                        className="absolute w-[6px] h-[6px] bg-black rounded-full"
                        style={{
                          top: '20px', // same baseline
                          left: `calc(${pos}% - 3px)`,
                          transform: 'translateY(-50%)',
                          zIndex: 11,
                        }}
                      />
                    );
                  })}
                  {(() => {
                    const posH = getRelativePosition(high);
                    return (
                      <div
                        className="absolute w-[6px] h-[6px] bg-gray-400 rounded-full"
                        style={{
                          top: '20px', // same baseline
                          left: `calc(${posH}% - 3px)`,
                          transform: 'translateY(-50%)',
                          zIndex: 11,
                        }}
                      />
                    );
                  })()}

                  {/* Resistance levels (unchanged) */}
                  {stockData.past_resistance.map((level, idx) => {
                    const pos = getRelativePosition(level);
                    return (
                      <div
                        key={`resistance-${idx}`}
                        className="absolute top-0 h-full transition-all duration-300"
                        style={{ left: `${pos}%` }}
                      >
                        <div className="relative h-full flex flex-col items-center -translate-x-1/2">
                          {/* Vertical line */}
                          <div className="w-px h-full bg-blue-400"></div>
                          {/* Price label */}
                          <div className="absolute -bottom-1 bg-red-500 text-white px-0.5 py-0.2 rounded text-[7px] font-semibold whitespace-nowrap shadow-sm">
                            {level.toFixed(2)}
                          </div>
                        </div>
                      </div>
                    );
                  })}

                  {/* Current position indicator (unchanged) */}
                  <div
                    className="absolute top-4 h-8 transition-all duration-700 ease-out"
                    style={{ left: `${dailyPosition}%` }}
                  >
                    <div className="relative flex flex-col items-center -translate-x-1/2">
                      {/* Value label */}
                      <div className="absolute -top-5 bg-blue-500 text-white px-1 py-0.5 rounded text-[9px] font-bold whitespace-nowrap shadow-sm">
                        <div className="absolute bottom-0 left-1/2 transform -translate-x-1/2 translate-y-1/2 rotate-45 w-1 h-1 bg-blue-500"></div>
                        {isPositive(stockData.curr_day_state.change) ? '+' : ''}
                        {stockData.curr_day_state.change}
                      </div>
                    </div>
                  </div>
                </div>

                {/* Scale markers (unchanged) */}
                <div className="relative flex justify-between text-[9px] font-medium text-gray-600">
                  <span className="text-gray-700 font-bold">0%</span>
                  <span className="text-green-300">+1</span>
                  <span className="text-green-400">+2</span>
                  <span className="text-green-500">+3</span>
                  <span className="text-green-600">+4</span>
                  <span className="text-green-700">+5</span>
                  <span className="text-green-800">+6</span>
                  <span className="text-green-900">+7</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default PoisitiveTradingCard;
