import json
import re
import time
from typing import Optional, List
from dataclasses import dataclass, field
import numpy as np
import requests
import pandas as pd
from tqdm.autonotebook import tqdm

# change these variables to change the fandom instance & character category/ies
FANDOM_SITE = 'coronationstreet'
CATEGORY = 'Coronation_Street_characters'
CATEGORIES = [CATEGORY]
JSON_FILE = f"projects/{FANDOM_SITE}.json"
FANDOM_URL = f'https://{FANDOM_SITE}.fandom.com'
API_URL = FANDOM_URL + '/api.php'

NAMESPACES = [
    ('-2', 'Media'),
    ('-1', 'Special'),
    ('0', 'Article'),
    ('1', 'Talk'),
    ('2', 'User'),
    ('3', 'User talk'),
    ('4', 'Project'),
    ('5', 'Project talk'),
    ('6', 'File'),
    ('7', 'File talk'),
    ('8', 'MediaWiki'),
    ('9', 'MediaWiki talk'),
    ('10', 'Template'),
    ('11', 'Template talk'),
    ('12', 'Help'),
    ('13', 'Help talk'),
    ('14', 'Category'),
    ('15', 'Category talk'),
    ('110', 'Forum'),
    ('111', 'Forum talk'),
    ('420', 'GeoJson'),
    ('421', 'GeoJson talk'),
    ('500', 'User blog'),
    ('501', 'User blog comment'),
    ('502', 'Blog'),
    ('503', 'Blog talk'),
    ('710', 'TimedText'),
    ('711', 'TimedText talk'),
    ('828', 'Module'),
    ('829', 'Module talk'),
    ('1200', 'Message Wall'),
    ('1201', 'Thread'),
    ('1202', 'Message Wall Greeting'),
    ('2000', 'Board'),
    ('2001', 'Board Thread'),
    ('2002', 'Topic'),
    ]


def remove_suffix(cell, suffix):
    if cell and cell.endswith(suffix):
        l = len(suffix)
        cell = cell[:-l]
    else:
        pass
    return cell


def remove_suffixes(df, col_list, suffix_list):
    for col in col_list:
        for suffix in suffix_list:
            df[col].loc[df[col].str.endswith(suffix, na=False)] = (df[col].loc[df[col].str.endswith(suffix, na=False)]
                                                         .apply(lambda x: remove_suffix(x, suffix))
                                                         .str.strip())
    return df

# These functions are for getting all pages in a category and their infoboxes.

def make_list_chunks(lst, n=50):
    """split a list up into sublist chunks of size n (default 50)"""
    return [lst[i:i + n] for i in range(0, len(lst), n)]

@dataclass
class WikiAPI:
    '''A base class for querying a fandom Wiki'''
    fandom_site: str = FANDOM_SITE
    fandom_url: str = FANDOM_URL
    api_url: str = API_URL
    category: Optional[str] = CATEGORY
    categories: Optional[list] = field(default_factory=list)
    namespaces: List = field(default_factory=list)
    params: dict = field(default_factory=dict)

    def __post_init__(self):
        self.namespaces = NAMESPACES
        self.params = {'action': 'query',
                       'format': 'json',
                      }

    def scrape(self):
        pass

    def parse(self):
        pass

    def build(self):
        self.scrape()
        self.parse()

    def get_all_namespaces(self, api_url=API_URL):
        params = {'action': 'query',
                  'format': 'json',
                  'meta': 'siteinfo',
                  'siprop': 'namespaces',
                  }
        r = requests.get(api_url, params=params)
        data = json.loads(r.text)
        namespaces = data['query']['namespaces']
        nses = [(k, v.get('canonical', '*')) for k, v in namespaces.items()]
        return nses

    def get_all_pages(self, namespace=None):
        '''Get all pages from a particular namespace (defaults to articles).'''
        params = {'action': 'query',
                'format': 'json',
                'list': 'allpages',
                'aplimit': '500',
                'apfilterredir': 'nonredirects',
                'apcontinue': '0',
                }
        if namespace is None:
            namespace = 0
        params.update({'apnamespace': namespace})
        all_pages = []
        cont = "0"
        while cont != "1":
            r = requests.get(API_URL, params=params)
            data = json.loads(r.text)
            pages = data['query']['allpages']
            pages = [(x['pageid'], x['title']) for x in pages]
            all_pages.extend(pages)
            try:
                apcontinue = data['continue']['apcontinue']
            except KeyError:
                apcontinue = "1"
            cont = apcontinue
            params.update({'apcontinue': apcontinue})
            time.sleep(1)
        return all_pages


@dataclass
class WikiCategory(WikiAPI):
    '''Given a category or list of categories, get the subcategories and the pages in those subcategories.
    Queries the API for both categories & pages at the same time.'''
    recursive: bool = True
    group_pages: bool = False

    def __post_init__(self):
        super().__post_init__()
        self.params.update({'list': 'categorymembers',
                            'cmtype': 'subcat|page',
                            'cmtitle': f'Category:{self.category}',
                            'cmlimit': 500,
                            'cmcontinue': '',
                            })
        if not self.categories:
            self.categories = [self.category]

    def scrape(self):
        self.category_members = self.get_category_members()
        self.subcats = self.category_members.get('subcats', None)
        self.pages = self.category_members.get('pages', None)
        if not self.group_pages:
            self.pageids = [x[0] for x in self.pages]
            self.titles = sorted([x[1] for x in self.pages])

    def get_category_members(self, categories=None, recursive=None, group_pages=None, params=None):
        if categories is None:
            categories = self.categories
        if recursive is None:
            recursive = self.recursive
        if group_pages is None:
            group_pages = self.group_pages
        if params is None:
            params = self.params
        items = {}
        items['categories'] = categories
        items['subcats'] = []
        if group_pages:
            items['pages'] = {}
        else:
            items['pages'] = []

        print('Retrieving category members:\n')
        for category in tqdm(items['categories']):
            params['cmtitle'] = f'Category:{category}'
            params['cmcontinue'] = 0
            while params['cmcontinue'] != 1:
                r = requests.get(API_URL, params=params)
                # print(r.url)
                data = json.loads(r.text)
                results = data['query']['categorymembers']
                subcats = [x['title'].replace('Category:', '') for x in results if int(x['ns']) == 14]
                items['subcats'].extend(subcats)
                pages = [(x['pageid'], x['title']) for x in results if int(x['ns']) == 0]
                if group_pages:
                    if not items['pages'].get(category, None):
                        items['pages'][category] = []
                    items['pages'][category].extend(pages)
                else:
                    items['pages'].extend(pages)
                if recursive:
                    # append new categories to the category list
                    items['categories'].extend(subcats)
                if 'batchcomplete' in data.keys():
                    params['cmcontinue'] = 1
                else:
                    params['cmcontinue'] = data['continue']['cmcontinue']
            time.sleep(1)
        # prune duplicates (pages likely to re-occur across multiple subcategories)
        if not group_pages:
            for k, v in items.items():
                items[k] = sorted(list(set(v)))
        return items


@dataclass
class WikiInfobox(WikiAPI):
    '''Given a list of wikipages, scrape their infoboxes.'''
    pages: Optional[list] = field(default_factory=list)
    titles: Optional[list] = field(default_factory=list)
    recursive: bool = True
    by_category: bool = True
    standardize_case: bool = True
    alert_empty: bool = True

    def __post_init__(self):
        super().__post_init__()
        self.params.update({
            'prop': 'revisions',
            'rvprop': 'content',
            'rvsection': '0',
            'rvslots': '*',
        })
        if self.pages and not self.titles:
            self.titles = [x[1] for x in self.pages]

    def scrape(self):
        if self.by_category:
            if not self.categories:
                self.categories = [self.category]
            if not self.pages and not self.titles:
                wikicat = WikiCategory(categories=self.categories, recursive=self.recursive)
                wikicat.scrape()
                self.pages = wikicat.pages
                self.pageids = wikicat.pageids
                self.titles = wikicat.titles
            elif not self.titles:
                self.pageids = [x[0] for x in self.pages]
                self.titles = [x[1] for x in self.pages]
        if self.titles:
            self.params.update({'titles': self.titles})
            self.raw_infoboxes = self.get_raw_infoboxes()
            self.matched_raw_infoboxes = self.match_names_to_infoboxes()

    def parse(self):
        if self.titles:
            self.unsorted_infoboxes = self.get_parsed_infoboxes()
            self.infoboxes = self.sort_infoboxes_by_template()
            self.dfs = self.build_dfs_infobox()
            if len(self.dfs) == 1:
                self.df = list(self.dfs.values())[0]

    def get_raw_infoboxes(self, titles=None, params=None):
        '''From a list of titles, get the raw json for their infoboxes'''
        if titles is None:
            titles = self.titles
        try:
            assert type(titles) == list
        except AssertionError:
            raise TypeError
        if params is None:
            params = self.params

        # break up titles into chunks of 50 or fewer
        title_chunks = make_list_chunks(titles)

        raw_infoboxes = {}
        print('Retrieving infoboxes for each page title:')
        for chunk in tqdm(title_chunks):
            time.sleep(1)  # add sleep so don't overwhelm server
            title_list = '|'.join([x for x in chunk])
            params.update({'titles': title_list})
            r = requests.get(API_URL, params=params)
            json_values = r.json()
            pages = json_values['query']['pages']
            boxes = {int(k): v['revisions'][0]['slots']['main']['*'] for k, v in pages.items() if int(k) > 0}
            # warn if missing infoboxes
            missing_boxes = {k: v for k, v in pages.items() if int(k) < 1}
            if missing_boxes:
                for v in missing_boxes.values():
                    print(f"Infobox page missing: {v['title']}")
            raw_infoboxes.update(boxes)

        return raw_infoboxes

    def process_value(self, val):
        """within the context of an infobox to be parsed, clean up the value after the '=' sign."""
        val = val.replace("[[","")
        val = val.replace("]]","")
        val = val.replace("}}","")
        val = val.replace("{{","")
        val = re.sub("([\(\[]).*?([\)\]])", "\g<1>\g<2>", val)
        val = val.replace("()","")

        val = val.lstrip('*').strip()

        #remove any training white spaces left
        ##if we have a br the k becomes an array

        if any(x in val for x in ['<br />', '<br>', '<br/>']):
            val = val.replace('<br />', '<br>').replace('<br/>', '<br>')
            val = val.split('<br>')
            val = [x.strip() for x in val]

        # transform true/false to boolean
        if type(val) == str and val.lower() == 'true':
            val = True
        elif type(val) == str and val.lower() == 'false':
            val = False
        return val

    def parse_infobox(self, info_json, standardize_case=None):
        if standardize_case is None:
            standardize_case = self.standardize_case
        infoboxes = {}
        infobox_name = ''
        k = ''
        json_lines = info_json.splitlines()
        for i, line in enumerate(json_lines):
            is_list = False
            if re.findall(r'\{\{Infobox.*?', line):
                infobox_name = re.findall(r'Infobox.*', line)[0].strip().replace('_', ' ')
                infoboxes[infobox_name] = {}
            elif line.startswith('|'):
                # process k
                k = line.partition('=')[0].strip()[1:]
                k = k.strip()
                if self.standardize_case:
                    k = k.lower()

                # process val
                val1 = line.partition('=')[-1].strip()
                val = self.process_value(val1)
                if type(val) == str and (val1.startswith('*') or not len(val)):
                    is_list = True
                    if val1.startswith('*'):
                        assert len(val1.split('*')) == 2
                        item_1 = val.lstrip('*').strip()
                        val = [item_1]
                    elif json_lines[i+1].startswith('*'):
                        val = []
                    else:
                        is_list = False
                    if is_list:
                        assert json_lines[i+1].startswith('*')
                        counter = 0
                        idx = i
                        while counter < 20:
                            # look ahead for other list members, stopping at next parameter field
                            if json_lines[idx+1].startswith('*'):
                                new_item = self.process_value(json_lines[idx+1])
                                val.append(new_item)
                                idx += 1
                                counter += 1
                            else:
                                break

                elif type(val) == str:
                    assert '*' not in val

                #process k
                if not infobox_name:
                    print('no infobox name:', k, val[:20])
                else:
                    infoboxes[infobox_name][k] = val

        return infoboxes

    def match_names_to_infoboxes(self,
                                 categories=None,
                                 pages=None,
                                 titles=None,
                                 pageids=None,
                                 infoboxes=None):
        '''Uses pageids to match title/name tuple to raw infobox json.'''
        if categories is None:
            categories = self.categories
        if pages is None:
            pages = self.pages
        if titles is None:
            if not hasattr(self, 'titles') or not self.titles:
                titles = [x[1] for x in pages]
            else:
                titles = self.titles
        if pageids is None:
            if not hasattr(self, 'pageids') or not self.pageids:
                pageids = [x[0] for x in pages]
            else:
                pageids = self.pageids
        if infoboxes is None:
            infoboxes = self.raw_infoboxes
        matched_raw_infoboxes = {}
        for pid in pageids:
            title = next(x[1] for x in pages if x[0] == pid)
            matched_raw_infoboxes[(pid, title)] = infoboxes[pid]
        return matched_raw_infoboxes

    def get_parsed_infoboxes(self, titles=None, raw_infoboxes=None, standardize_case=None):
        '''Parses the raw infoboxes into dicts from matched title json dict.'''
        if titles is None and raw_infoboxes is None:
            titles = self.titles
        if raw_infoboxes is None:
            raw_infoboxes = self.raw_infoboxes
        if standardize_case is None:
            standardize_case = self.standardize_case

        matched_infoboxes = self.match_names_to_infoboxes(titles=titles, infoboxes=raw_infoboxes)

        infoboxes = {k: self.parse_infobox(v, standardize_case=standardize_case) for k, v in matched_infoboxes.items()}
        return infoboxes

    def get_infoboxes_for_title(self, title, standardize_case=None, parsed=True):
        """For a single title, get the article infoboxes. Do not use to iterate!
        Use chunking via `self.get_parsed_infoboxes()` instead."""
        if standardize_case is None:
            standardize_case = self.standardize_case
        title = '_'.join(title.split())
        fullurl = '/'.join([FANDOM_URL, title])
        r = requests.get(fullurl, params={'action': 'raw',
                                          'section': '0',
                                          'format': 'json',
                                          })
        page = r.text
        if parsed:
            parsed_infobox = self.parse_infobox(page, standardize_case=standardize_case)
            return parsed_infobox
        else:
            return page

    def write_infobox_json(self, categories=None, df=None):
        '''Output infobox dict to json file'''
        if categories is None:
            categories = self.categories
        if df is None:
            df = next(iter(self.dfs.values()))
        df = df.set_index('page_title', drop=True)
        json_data = df.to_json(indent=4, orient='index')
        with open(JSON_FILE, 'w') as f:
            f.write(json_data)

    def sort_infoboxes_by_template(self, infoboxes=None, alert_empty=None):
        if alert_empty is None:
            alert_empty = self.alert_empty
        if infoboxes is None:
            infoboxes = self.unsorted_infoboxes
        sorted_infoboxes = {}
        for k, v in infoboxes.items():
            for infobox_name, infobox in v.items():
                if not sorted_infoboxes.get(infobox_name, None):
                    sorted_infoboxes[infobox_name] = {}
                sorted_infoboxes[infobox_name][k] = infobox
        if alert_empty:
            empty = [k for k, v in infoboxes.items() if not v.values()]
            if len(empty):
                print(f"These entries are missing infoboxes and will not be in df: {empty}")
        return sorted_infoboxes

    def build_df_infobox(self, infoboxes):
        df = pd.DataFrame.from_dict(infoboxes, orient='index')
        df.index.set_names(["pageid", "page_title"], inplace=True)
        df = df.reset_index()
        df.pageid = df.pageid.astype(int)
        df = df.replace('PAGENAME', np.NaN)
        return df

    def build_dfs_infobox(self, infoboxes=None):
        if infoboxes is None:
            infoboxes = self.infoboxes
        dfs_dict = {}
        for infobox_name, val in infoboxes.items():
            dfs_dict[infobox_name] = self.build_df_infobox(val)
            df_name = 'df_' + infobox_name.replace('Infobox ', '').lower()
            setattr(self, df_name, dfs_dict[infobox_name])
        return dfs_dict


if __name__ == "__main__":
    print(f'Getting {CATEGORIES} infoboxes from fandom site {FANDOM_SITE}\n')
    # create WikiInfobox instance with default values
    wi = WikiInfobox(categories=CATEGORIES, recursive=False)
    wi.build()

    # output primary infobox dataframe to json file
    print(f'Writing infoboxes to {JSON_FILE}\n')
    wi.write_infobox_json()

