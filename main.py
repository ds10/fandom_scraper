import requests
import time
import urllib.request
import json
import re
import ssl
from tqdm import tqdm

# change these variables to change the fandom instance & character category/ies
FANDOM_SITE = 'coronationstreet'
CATEGORY = 'Coronation_Street_characters'
CATEGORIES = [CATEGORY]

JSON_FILE = f"projects/{FANDOM_SITE}.json"
FANDOM_URL = f'https://{FANDOM_SITE}.fandom.com'
API_URL = FANDOM_URL + '/api.php'
BASE_QUERY_URL = API_URL + '?action=query&format=json&list=categorymembers&cmtitle=Category:'
URL_SUFFIX = '&cmlimit=500&cmcontinue='
SSL_CONTEXT = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)


def make_list_chunks(lst, n=50):
    """split a list up into sublist chunks of size n (default 50)"""
    return [lst[i:i + n] for i in range(0, len(lst), n)]


def get_category_pages(fullurl=None):
    """Gets names in category, including `pageid` in tuple (for later matching).
    Replaces `extractURLs`."""
    if fullurl is None:
        fullurl = BASE_QUERY_URL + CATEGORY + URL_SUFFIX
    # print(fullurl)
    names = []
    with urllib.request.urlopen(fullurl, context=SSL_CONTEXT) as url:
        data = json.loads(url.read().decode())
        for item in data['query']['categorymembers']:
            name_tuple = (item['pageid'], item['title'])
            names.append(name_tuple)

    # the API returns a value under `cmcontinue` if there are more results than listed,
    # to enable successive queries. if no value there, stop while loop with '1'.
    cmcontinue = data.get('continue', {}).get('cmcontinue', "1")

    return cmcontinue, names


def get_titles(categories=CATEGORIES):
    '''Gives previous functionality from `if __name__ == 'main'` ability to handle multiple categories.'''
    titles = []
    for category in tqdm(categories):
        cont = "0"
        while cont != "1":
            url = ''.join([BASE_QUERY_URL, category, URL_SUFFIX, cont])
#             print(url)
            cmcontinue, pages = get_category_pages(fullurl=url)

            # prune pages that aren't for specific characters
            pages_refined = [x for x in pages if "Category:" not in x[1]]
            titles.extend(pages_refined)
            cont = cmcontinue
    return titles


def get_raw_infoboxes(titles=None, categories=CATEGORIES, sleep=1):
    '''From a list of title tuples, get the raw json for their infoboxes. This is a bulk query that
    only gets the first section of the article instead of the full text. `pageid` is the dict key.
    Uses tqdm to track progress.'''
    if titles is None:
        titles = get_titles(categories=categories)
    try:
        assert type(titles) == list
        assert type(sleep) == int or type(sleep) == float
    except AssertionError:
        raise TypeError

    # break up title tuples into chunks of 50 or fewer, max for API infobo xquery
    title_chunks = make_list_chunks(titles)

    raw_infoboxes = {}
    for chunk in tqdm(title_chunks):
        time.sleep(sleep)  # add sleep so don't overwhelm server
        title_list = '|'.join([x[1] for x in chunk])
        params={'action': 'query',
                'titles': title_list,
                'format': 'json',
                'prop': 'revisions',
                'rvprop': 'content',
                'rvsection': '0',
                'rvslots': '*'}
        r = requests.get(API_URL, params=params)
        # print(r.url)
        json_values = r.json()
        pages = json_values['query']['pages']

        boxes = {int(k): v['revisions'][0]['slots']['main']['*'] for k, v in pages.items()}
        raw_infoboxes.update(boxes)

    return raw_infoboxes


def parse_infobox(info_json):
    '''Adapts parsing functionality from `extractBoxes` to have input of raw json.
    Outputs to dict format.'''
    data = {}
    for line in info_json.splitlines():
        if line.startswith('|'):
            val = line.partition('=')[-1].strip() #val  
            #process value
            val = val.replace("[[","")
            val = val.replace("]]","")
            val = val.replace("}}","")
            val = val.replace("{{","")
            val = re.sub("([\(\[]).*?([\)\]])", "\g<1>\g<2>", val)
            val = val.replace("()","") 

            val = val.strip() 

            if any(x in val for x in ['<br />', '<br>', '<br/>']):
                val = val.replace('<br />', '<br>').replace('<br/>', '<br>')
                val = val.split('<br>')
                val = [x.strip() for x in val]

            k = line.partition('=')[0].strip()[1:] #key
            k = k.strip()

            #process k
            data[k] = val
    return data


def match_names_to_infoboxes(categories=None,
                             titles=None,
                             infoboxes=None):
    '''Uses `pageid` to match title/name tuple to raw infobox json.'''
    if not categories:
        categories = CATEGORIES
    if not titles:
        titles = get_titles(categories=categories)
    if not infoboxes:
        infoboxes = get_raw_infoboxes(titles)

    raw_infobox_dict = {}
    page_numbers = [x[0] for x in titles]
    for pn in page_numbers:
        title = next(x[1] for x in titles if x[0] == pn)
        raw_infobox_dict[title] = infoboxes[pn]
    return raw_infobox_dict


def get_parsed_infoboxes(categories=CATEGORIES, titles=None, raw_infoboxes=None):
    '''Parses the raw infoboxes into dicts from matched title json dict.'''
    if titles is None and raw_infoboxes is None:
        titles = get_titles(categories=categories)
    if raw_infoboxes is None:
        raw_infoboxes = get_raw_infoboxes(titles=titles)

    matched_infoboxes = match_names_to_infoboxes(titles=titles, infoboxes=raw_infoboxes)

    infoboxes = {k: parse_infobox(v) for k, v in matched_infoboxes.items()}
    return infoboxes


def get_infoboxes(categories=CATEGORIES):
    '''combines functions to get full pipeline of category list to parsed infoboxes dict,
    sorted by title.'''
    print('Retrieving page titles in categories:')
    titles = get_titles(categories=categories)

    print('\nRetrieving infoboxes for each page title:')
    infoboxes = get_parsed_infoboxes(titles=titles)
    return infoboxes


def write_infobox_json(categories=CATEGORIES, infoboxes=None, json_file=JSON_FILE):
    '''Output infobox dict to json file'''
    if infoboxes is None:
        infoboxes = get_infoboxes(categories=categories)
    json_data = json.dumps(infoboxes, indent=4, sort_keys=True)
    with open(json_file, 'w') as f:
        f.write(json_data)


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
    print(f'Getting {CATEGORIES} infoboxes from fandom site {FANDOM_SITE}\n')
    # create infobox dict
    infoboxes = get_infoboxes(categories=CATEGORIES)

    # output infobox dict to json file
    print('Writing infoboxes to .json file\n')
    write_infobox_json(infoboxes=infoboxes)

