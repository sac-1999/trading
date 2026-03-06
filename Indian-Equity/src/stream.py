
# app.py
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from flask import Flask, Response, stream_with_context
import redis, threading

import numpy as np
import pandas as pd
import time 
from streamutils import *

app = Flask(__name__)
_DATE = datetime.today()
EXCHANGE = 'NSE'
INDEX = 'Nifty 50'



def update_symbol_state():  # publishes a new value every second
    
    while True:
        listofsymbols = []
        losers = load_top_losers()
        gainers = load_top_gainers()
        allindices = get_indexlist()
        if losers is not None:
            losers = json.loads(losers)     
            listofsymbols.extend(losers)
        if gainers is not None:
            gainers = json.loads(gainers)
            listofsymbols.extend(gainers)
        # print('gainers : ' , gainers)
        # print('losers :' , losers)
        print(listofsymbols)
        for symbol in listofsymbols:
            channel = f"{symbol}-channel"
            msg = get_allstate_for_symbol(EXCHANGE, symbol, False)
            if msg is not None:
                r.publish(channel, msg)
 
        if allindices is not None:
            allindices = json.loads(allindices)
            for indice in allindices:
                channel = f"{indice}-channel"
                msg = get_state_for_index(indice)
                if msg is not None:
                    r.publish(channel, msg)

        # time.sleep(0.5)


threading.Thread(target=update_symbol_state, daemon=True).start()
# threading.Thread(target=listen, daemon=True).start()



import json
import time

def sse_pubsub_generator(pattern="*-channel", heartbeat_interval=15):
    pubsub = r.pubsub()
    pubsub.psubscribe(pattern)
    last_heartbeat = time.time()

    try:
        for message in pubsub.listen():
            now = time.time()

            # Heartbeat (comment line per SSE spec)
            if now - last_heartbeat >= heartbeat_interval:
                # Ensure a blank line follows the comment
                yield ": keepalive\n\n"
                last_heartbeat = now

            if message.get("type") == "pmessage":
                raw = message.get("data")

                # Decode JSON payload robustly
                try:
                    if isinstance(raw, (bytes, bytearray)):
                        payload = json.loads(raw.decode("utf-8"))
                    elif isinstance(raw, str):
                        payload = json.loads(raw)
                    else:
                        payload = {"raw": str(raw)}
                except Exception:
                    payload = {
                        "raw": raw.decode() if isinstance(raw, (bytes, bytearray)) else str(raw)
                    }

                # Consistent event type
                event_name = "update"

                # Use provided timestamp or fallback to current time in ms
                event_id = str(payload.get("ts", int(now * 1000)))

                # IMPORTANT: Each event must end with a blank line
                yield f"id: {event_id}\n"
                yield f"event: {event_name}\n"
                yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"

            # tiny sleep to avoid busy loop
            time.sleep(0.01)
    finally:
        try:
            pubsub.close()
        except Exception:
            pass



@app.get("/stream")
def stream():
    # You can read Last-Event-ID here, but with Pub/Sub we can’t replay. Use Streams if you need replay.
    # last_event_id = request.headers.get('Last-Event-ID')
    resp = Response(stream_with_context(sse_pubsub_generator()),
                    mimetype="text/event-stream")
    # Important headers
    resp.headers["Cache-Control"] = "no-cache"
    resp.headers["Connection"] = "keep-alive"
    resp.headers["X-Accel-Buffering"] = "no"  # for nginx
    resp.headers["Access-Control-Allow-Origin"] = "*"  # adjust for your domain
    return resp


app.run(port=5000)
