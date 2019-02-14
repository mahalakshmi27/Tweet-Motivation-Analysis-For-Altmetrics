import re
import json
import math
import pandas as pd
from requests import get
from bs4 import BeautifulSoup
from openpyxl import load_workbook

def getAllTweetsFromPage(tweet_container, doi, alt_id, details):
    global df
    for tweet in tweet_container:
        uname = tweet.find('div', attrs={'class': 'name'}).text
        handle = tweet.find('div', attrs={'class': 'handle'}).text
        user_url = tweet.a.get('href')
        fc = tweet.find('div', attrs={'class': 'follower_count'}).text
        content = tweet.find('p', attrs={'class':'summary'}).text
        if tweet.find('time'):
            time = tweet.find('time').text
            tweet_url = tweet.find('time').a.get('href')
        img = tweet.find('div', attrs={'class':'avatar-holder'})
        image_url = re.match("background-image: url\(([^\)]+)\)", img.get('style')).groups()[0] if img else None
        #print(uname, handle, user_url, image_url)
        temp = {'alt_id':alt_id, 'doi': doi, 'username':uname, 'handle':handle, 'user_url':user_url, 'follower_count':fc, 'content':content, 'tweet_url':tweet_url, 'time':time, 'image_url':image_url}
        temp.update(details)
        df = df.append(temp, ignore_index=True)
    print("Fetched all tweets in page!")

def getSummary(alt_id):
    global keys
    details = {}
    summary_url = 'https://explorer.altmetric.com/details/%s'%str(alt_id)
    resp = get(summary_url)
    html_soup = BeautifulSoup(resp.text, 'html.parser')
    rows = html_soup.find('div', class_='document-details-table').find('table').find_all('tr')
    for row in rows:
        key = row.find('th').text
        if key in keys:
            details[keys[key]] = row.find('td').text
    #print("Returning summary for", alt_id)
    return details

k=100
med_master = pd.read_csv('altmetric_ids.csv')
ids_list = list(zip(med_master.DI, med_master.altmetric_id))
keys = {'Title':'title', 'Published in':'pub_name', 'Pubmed ID':'pub_id', 'Authors':'authors', 'Abstract':'abstract'}
for n in range(k,len(ids_list),k):
    #print("ALERT: Loop "+str(n-100)+"!!")
    ids_tuple = ids_list[n-k:n]
    for i, ids in enumerate(ids_tuple):
        doi, alt_id = ids[0], ids[1]
        if math.isnan(alt_id):
            resp = get('https://api.altmetric.com/v1/doi/%s'%str(doi))
            if resp.text == 'Not Found':
                print('Altmetrics id unavailable!')
                continue
            else:
                resp = json.loads(resp.text)
                if resp.get('altmetric_id'):
                    alt_id = int(resp.get('altmetric_id'))
                else:
                    print('Altmetrics id unavailable!')
                    continue
            print("Fetched Altmetrics ID using Altmetrics API:", alt_id)
        else:
            alt_id = int(alt_id)
        df = pd.DataFrame(columns=['doi', 'title', 'pub_name', 'pub_id', 'authors', 'abstract', 'alt_id', 'username', 'handle', 'user_url','follower_count','content', 'tweet_url', 'time','image_url'])
        details = getSummary(alt_id)
        #Fetching the first page
        url='https://explorer.altmetric.com/details/%s/twitter/page:1'%str(alt_id)
        resp = get(url)
        #Scraping the first page
        html_soup = BeautifulSoup(resp.text, 'html.parser')
        tweet_container = html_soup.find_all('article', class_='post twitter')
        #Fetching the number of tweet pages
        if tweet_container:
            totalTweets = re.findall('\d+',html_soup.find('div', class_='text').text)[0]
            pages = math.ceil(int(totalTweets)/len(tweet_container))
            getAllTweetsFromPage(tweet_container, doi, alt_id, details)
            #Scraping and fetching details from other pages
            for page in range(2,pages+1):
                print("Scrapping page:",page)
                url='https://explorer.altmetric.com/details/'+str(alt_id)+'/twitter/page:'+str(page)
                resp = get(url)
                html_soup = BeautifulSoup(resp.text, 'html.parser')
                tweet_container = html_soup.find_all('article', class_='post twitter')
                getAllTweetsFromPage(tweet_container, doi, alt_id, details)
            #Writing to Excel
            path = 'altmetrics'+str(n-(k-1))+'-'+str(n)+'.xlsx'
            book = load_workbook(path)
            writer = pd.ExcelWriter(path, engine='openpyxl')
            writer.book = book
            df.to_excel(writer, sheet_name='Article'+str(i+1))
            writer.save()
            writer.close()
            print("Data for Article "+str(i+1)+" dumped in excel!")
        else:
            print("No tweets for alt id:"+str(alt_id))
print("ALERT: Data scrapped!")
