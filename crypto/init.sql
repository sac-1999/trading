-- Enable TimescaleDB
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- Stock OHLCV table
CREATE TABLE IF NOT EXISTS stock_ohlcv (
    time        TIMESTAMPTZ NOT NULL,
    symbol      TEXT NOT NULL,
    timeframe   TEXT NOT NULL,   -- 1m, 5m, 15m, 1h, 1d
    open        DOUBLE PRECISION,
    high        DOUBLE PRECISION,
    low         DOUBLE PRECISION,
    close       DOUBLE PRECISION,
    volume      BIGINT,

    PRIMARY KEY (symbol, timeframe, time)
);

-- Convert to hypertable
SELECT create_hypertable(
    'stock_ohlcv',
    'time',
    chunk_time_interval => INTERVAL '1 day',
    if_not_exists => TRUE
);

-- Query-optimized index
CREATE INDEX IF NOT EXISTS idx_stock_time
ON stock_ohlcv (symbol, timeframe, time DESC);


CREATE MATERIALIZED VIEW stock_ohlcv_5m
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('5 minutes', time) AS time,
    symbol,
    first(open, time)  AS open,
    max(high)          AS high,
    min(low)           AS low,
    last(close, time)  AS close,
    sum(volume)        AS volume
FROM stock_ohlcv
WHERE timeframe = '1m'
GROUP BY 1, 2;




SELECT add_continuous_aggregate_policy(
  'stock_ohlcv_5m',
  start_offset => INTERVAL '1 day',
  end_offset   => INTERVAL '1 minute',
  schedule_interval => INTERVAL '1 minute'
);
