import requests
import requests
def get_product_id_by_symbol(symbol = None):
    headers = {
    'Accept': 'application/json'
    }

    r = requests.get('https://api.india.delta.exchange/v2/products/', params={}, headers = headers)
    r = r.json()
    try:
        for i in r['result']:
            if i['contract_type'] == 'perpetual_futures' and i['symbol'] == symbol:
                return i['id']
    except Exception as e:
        print(e)
    return None