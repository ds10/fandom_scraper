import requests
import urllib.request
import json
import re



def extractBox(url="https://coronationstreet.fandom.com/",name="Amy_Barlow"):
    #xyz = 'Stella_Price'
    print(name)
    fullurl = url + name
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

              if("<br>" in value):
                     ##value = value.partition('<br>')
                     ##value = [x for x in value if x != "<br>"]
                     ##value = [x.strip() for x in value]
                     value = value.split('<br>')
                     value = [x.strip() for x in value]

              key = line.partition('=')[0].strip()[1:] #key

              #process key
              try:
                     data[name][key] = value
              except:
                     data[name] = {}
                     data[name][key] = value
      
    #json_data = json.dumps(data, indent=4, sort_keys=True)


    return(data)



def extractURLs(fullurl):
    print(fullurl)
    names = []
    with urllib.request.urlopen(fullurl) as url:
        data = json.loads(url.read().decode())
        for item in data['query']['categorymembers']: 
            for key in item:
                    if key == "title":  
                        names.append(item[key])
    try:
        cmcontinue = data['query-continue']['categorymembers']['cmcontinue']
    except:
        cmcontinue = "1"

       
    return cmcontinue, names


if __name__ == "__main__":

       cont = "0"
       titles = []

       while cont != "1": 
              result = extractURLs("https://coronationstreet.fandom.com//api.php?action=query&format=json&list=categorymembers&cmtitle=Category:Coronation_Street_characters&cmlimit=500" + "&cmcontinue=" + cont)
              cont = result[0]
              titles = result[1]


       full_data = {}

       for title in titles:
              full_data[title] = extractBox(url="https://coronationstreet.fandom.com/",name=title)


       json_data = json.dumps(full_data, indent=4, sort_keys=True)

       f = open("json_data.json", 'w') 
       f.write(json_data)

