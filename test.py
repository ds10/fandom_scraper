import requests
import json


xyz = 'Sinead_Osbourne'
url = 'https://coronationstreet.fandom.com/wiki/' + xyz
resp = requests.get(url, params={'action': 'raw'})
page = resp.text

data = {}

for line in page.splitlines():
       if line.startswith('|'):
              data[line.partition('=')[0].strip()] = line.partition('=')[-1].strip()
              


json_data = json.dumps(data)
print(json_data) 
