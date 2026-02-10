import json
from urllib.request import urlopen

resp = urlopen('http://127.0.0.1:8000/openapi.json')
data = json.load(resp)
paths = sorted(data.get('paths', {}).keys())
print('\n'.join(paths))
