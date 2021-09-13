import requests
import urllib.request
import json
import re


if __name__ == "__main__":

    csv = ""

    with open('coronationstreet.json') as data_file:
        data = json.load(data_file)
        for v in data.items():
            try:
                if isinstance(v[1]['spouse(s)'], list):
                    print ("a list!")
                    for itemsv in v[1]['spouse(s)']:
                        if v[1]['spouse(s)'] != "":
                            csv = csv + v[0] + "," + itemsv + "\n"
                            print("writing the following line")
                            print(v[0] + "," + v[1]['spouse(s)'] + "\n")
                else:
                    print ("not a list")
                    if v[1]['spouse(s)'] != "":
                        print("writing the following line")
                        print(v[0] + "," + v[1]['spouse(s)'] + "\n")
                        csv = csv + v[0] + "," + v[1]['spouse(s)'] + "\n"

                
            except:
                print("Doing nothing")
        
        print(csv)
        f = open("corrie.csv", 'w') 
        f.write(csv)