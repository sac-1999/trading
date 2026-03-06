
# sse_client.py
import requests

def sse_client(url="http://localhost:5000/stream"):
    print(url)
    with requests.get(url, stream=True) as r:
        print('inside')
        r.raise_for_status()
        print("Connected to SSE:", url)
        for line in r.iter_lines(decode_unicode=True):
            if not line:
                continue
            if line.startswith("data:"):
                print(line[5:].strip())  # print message payload
            # Optional: handle custom events like "heartbeat"
            elif line.startswith("event:"):
                evt = line[6:].strip()
                if evt == "heartbeat":
                    pass  # ignore or log heartbeat

if __name__ == "__main__":
    sse_client()
