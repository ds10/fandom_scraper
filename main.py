import requests
import urllib.request
import json
import re
import ssl

# change these two variables to change the fandom instance & character category
FANDOM_SITE = 'coronationstreet'
CATEGORY = 'Coronation_Street_characters'

FANDOM_URL = f'https://{FANDOM_SITE}.fandom.com'
API_URL = FANDOM_URL + '/api.php'
BASE_QUERY_URL = API_URL + '?action=query&format=json&list=categorymembers&cmtitle=Category:'
URL_SUFFIX = '&cmlimit=500&cmcontinue='
SSL_CONTEXT = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)


def extractBox(url=FANDOM_URL,name="Amy_Barlow"):
    #xyz = 'Stella_Price'
    print(name)
    name = '_'.join(name.split())
    fullurl = '/'.join([url, name])
    resp = requests.get(fullurl, params={'action': 'raw'})
    page = resp.text

    data = {}
    json_data = {}

    for line in page.splitlines():
        if line.startswith('|'):
            value = line.partition('=')[-1].strip() #value  
            #process value
            value = value.replace("[[","")
            value = value.replace("]]","")
            value = value.replace("}}","")
            value = value.replace("{{","")
            value = re.sub("([\(\[]).*?([\)\]])", "\g<1>\g<2>", value)
            value = value.replace("()","") 

            value = value.strip() 

            #remove any training white spaces left
            ##if we have a br the key becomes an array

            if any(x in value for x in ['<br />', '<br>', '<br/>']):
                value = value.replace('<br />', '<br>').replace('<br/>', '<br>')
                ##value = value.partition('<br>')
                ##value = [x for x in value if x != "<br>"]
                ##value = [x.strip() for x in value]
                value = value.split('<br>')
                value = [x.strip() for x in value]

            key = line.partition('=')[0].strip()[1:] #key
            key = key.strip()

            #process key
            try:
                data[key] = value
            except:
                data = {}
                data[key] = value

    #json_data = json.dumps(data, indent=4, sort_keys=True)


    return data



def extractURLs(fullurl):
    print(fullurl)
    names = []
    with urllib.request.urlopen(fullurl, context=SSL_CONTEXT) as url:
        data = json.loads(url.read().decode())
        for item in data['query']['categorymembers']: 
            for key in item:
                    if key == "title":
                        names.append(item[key])
    try:
        cmcontinue = data['continue']['cmcontinue']
    except KeyError:
        cmcontinue = "1"
    return cmcontinue, names


if __name__ == "__main__":

    cont = "0"
    titles = []

    while cont != "1":
        url = ''.join([BASE_QUERY_URL, CATEGORY, URL_SUFFIX, cont])
        result = extractURLs(url)
        titles.extend(result[1])
        cont = result[0]

    # filter out Category pages
    titles = [x for x in titles if "Category:" not in x]

    full_data = {}

    for title in titles:
        full_data[title] = extractBox(url=FANDOM_URL,name=title)

    json_data = json.dumps(full_data, indent=4, sort_keys=True)

    with open("fandom.json", 'w') as f:
        f.write(json_data)

