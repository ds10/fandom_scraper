import requests
import urllib.request
import json
import re
import ssl

SSL_CONTEXT = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)



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
              key = key.strip()

              #process key
              try:
                     data[key] = value
              except:
                     data = {}
                     data[key] = value
      
    #json_data = json.dumps(data, indent=4, sort_keys=True)


    return(data)



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
              titles.append(result[1])

       full_data = {}

       for title in titles:
              for wtf in title:
                     full_data[wtf] = extractBox(url="https://coronationstreet.fandom.com/",name=wtf)

       json_data = json.dumps(full_data, indent=4, sort_keys=True)

       f = open("json_data.json", 'w') 
       f.write(json_data)

