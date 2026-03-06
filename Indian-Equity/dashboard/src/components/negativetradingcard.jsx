import React, { useState } from 'react';
import { Activity } from 'lucide-react';

const NegativeTradingCard = ({stockData}) => {
  console.log(stockData)
  const getPosition = (percentage) => {
    const clamped = Math.max(-7, Math.min(0, percentage));
    return 100 - ((Math.abs(clamped) / 7) * 100);
  };

  // Calculate support positions relative to current price
  const getRelativePosition = (level) => {
    const percentDiff = ((level - stockData.last_day_state.close) / stockData.last_day_state.close) * 100;
    return getPosition(percentDiff);
  };

  const dailyPosition = getPosition(stockData.curr_day_state.change);

  return (
    <div className="bg-white">
      <div className="w-full">
        {/* Main Card */}
        <div className="bg-white rounded border border-gray-200">
          
          {/* Daily Change Scale Bar */}
          <div>
            <div className="relative">
              <div className="relative bg-gray-50 rounded p-1 border border-gray-100">
                {/* Stock Name - Absolute Position */}
                <div className="absolute top-1 left-2 z-20">
                  <span className="text-[10px] font-bold text-gray-700 bg-white/80 px-1 rounded">{stockData.symbol}</span>
                </div>

                <div className="relative h-5">
                  {/* Gradient Background */}
                  <div className="absolute inset-x-0 top-3 h-6 rounded overflow-hidden">
                    <div className="absolute inset-0 bg-gradient-to-r from-red-100 via-red-50 to-yellow-50"></div>
                  </div>
                  
                  {/* Support levels */}
                  {stockData.past_support.map((level, idx) => {
                    const pos = getRelativePosition(level);
                    return (
                      <div key={`support-${idx}`} className="absolute top-0 h-full transition-all duration-300" style={{ left: `${pos}%` }}>
                        <div className="relative h-full flex flex-col items-center -translate-x-1/2">
                          {/* Vertical line */}
                          {/* <div className="w-px h-full bg-gradient-to-b from-green-200/0 via-green-400 to-green-200/0"></div> */}
                          <div className="w-px h-full bg-green-400"></div>
                          
                          {/* Price label */}
                          <div className="absolute -bottom-1 bg-green-500 text-white px-0.5 py-0.2 rounded text-[7px] font-semibold whitespace-nowrap shadow-sm">
                            {level.toFixed(2)}
                          </div>  
                        </div>
                      </div>
                    );
                  })}

                  {/* Current position indicator */}
                  <div className="absolute top-4 h-8 transition-all duration-700 ease-out" style={{ left: `${dailyPosition}%` }}>
                    <div className="relative flex flex-col items-center -translate-x-1/2">
                      {/* Pulsing ring */}
                      {/* <div className="absolute top-1 w-4 h-4 bg-red-300 rounded-full animate-ping"></div> */}
                      
                      {/* Main indicator */}
                      {/* <div className="relative w-4 h-4 bg-gradient-to-br from-red-400 to-red-600 rounded-full border-2 border-white shadow-md flex items-center justify-center">
                        <Activity size={12} className="text-white" />
                      </div> */}
                      
                      {/* Value label */}
                      <div className="absolute -top-5 bg-red-500 text-white px-1 py-0.5 rounded text-[9px] font-bold whitespace-nowrap shadow-sm">
                        <div className="absolute bottom-0 left-1/2 transform -translate-x-1/2 translate-y-1/2 rotate-45 w-1 h-1 bg-red-500"></div>
                        {stockData.curr_day_state.change}
                      </div>
                    </div>
                  </div>
                </div>

                {/* Scale markers */}
                <div className="relative flex justify-between text-[9px] font-medium text-gray-600">
                  <span className="text-red-900">-7</span>
                  <span className="text-red-800">-6</span>
                  <span className="text-red-700">-5</span>
                  <span className="text-red-600">-4</span>
                  <span className="text-red-500">-3</span>
                  <span className="text-red-400">-2.5</span>
                  <span className="text-red-400">-2</span>
                  <span className="text-red-300">-1</span>
                  <span className="text-gray-700 font-bold">0%</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default NegativeTradingCard;