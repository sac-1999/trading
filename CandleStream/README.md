# Candlestream

**Candlestream** is a Python package designed to load historical candle data quickly using a custom caching system. It is optimized to provide fast access to market data and supports various trading-related functionalities.

## Features

- Fetches historical candle data with fast caching.
- Easily configurable for different data sources and time intervals.
- Simple API for fetching and manipulating candle data.
- Supports various indicators and technical analysis tools via integration with `pandas_ta`.
  
## Installation

### PyPI

You can install the package directly from PyPI:

```bash
pip install candlestream

### Use
create a .env file in your project. EX->

INTRA_API_KEY=kefhwaioty
INTRA_SECRET_KEY=487hcfwisy091748934-f5bfisekt37865c1-4d7fwisckuy75637284d-9dfiufcje5782438-33gfej6764343a90c
INTRA_PIN=011843204
INTRA_CLIENT_ID=njwh8235689
ANGLETOKEN=fjksehkw5746598 


Assign path to your .env in enviroment variable BROKER_ENV_FILE_PATH

How to use it 

from CandleStream import CandleStream 
from datetime import datetime, timedelta
stream = CandleStream()
df = stream.fetch_data('NSE', 'TCS', 11536, datetime.today() - timedelta(100), datetime.today())
print(df)
```

output :
<img width="339" alt="image" src="https://github.com/user-attachments/assets/f601b1e5-6860-4f6e-84dd-a3c3d39ccd50" />
