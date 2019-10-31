import requests
import urllib.request
import json
import re


if __name__ == "__main__":

    with open('json_data.json') as data_file:
        data = json.load(data_file)
        for v in data.keys():
            print()
            print(type(data[v]))
            for l in data[v].items():
                print(l)
                print(type(l[1]))
                for f in l[1].items():
                    print(f)
                    print(type(f))

            