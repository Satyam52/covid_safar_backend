from flask import Flask, render_template, url_for, request, redirect, jsonify, json
import requests
import datetime
from datetime import datetime
from bs4 import BeautifulSoup as bs
from urllib.request import Request, urlopen as uOpen
from bson.json_util import dumps
import os
from firebase_admin import credentials, firestore, initialize_app
from flask_cors import CORS
from covid_diaries_nlp import CovidDiariesNLP

app = Flask(__name__)
CORS(app)

# initialize database
try:
    cred = credentials.Certificate('key.json')
    default_app = initialize_app(cred)
    db = firestore.client()
    db_ref = db.collection('stories')
    print("Successful DataBase connection")
except Exception as e:
    print(f"An Error Occured: {e}")


# adding story(using scheduler)
@app.route('/toi', methods=['POST', 'GET'])
def index():
    searchString = 'my-covid-story'   # can have list of keywords
    # searchString = request.json['content']   #if we want to search custom string via front end

    newsUrl = "https://timesofindia.indiatimes.com/life-style/health-fitness/" + \
        searchString.strip()
    req = Request(newsUrl, headers={'User-Agent': 'Mozilla/5.0'})
    newsPage = uOpen(req).read()
    newsPageHtml = bs(newsPage, "html.parser")
    eachNews = newsPageHtml.findAll("span", {"class": "md_news_leftin"})
    allNewsLinks = []

    for i in eachNews:
        allNewsLinks.append(i.a['href'])

    allStoryLinksInDB = []
    for doc in db_ref.stream():
        allStoryLinksInDB.append(doc.to_dict()['link'])

    saveCount = 0
    passCount = 0

    for i in allNewsLinks:
        link = "https://timesofindia.indiatimes.com" + i
        if link in allStoryLinksInDB:
            print(f"pass {passCount}")
            passCount += 1
            pass
        else:
            try:
                req = requests.get(link)
                req.encoding = 'utf-8'
                singleNewsPageHtml = bs(req.text, "html.parser")
                heading = singleNewsPageHtml.find(
                    "arttitle").text
                content = singleNewsPageHtml.find(
                    "div", {"class": "Normal"}).text
                garbage = "Did you fight COVID-19? We want to hear all about it. ETimes Lifestyle is calling all the survivors of COVID to share their stories of survival and hope.Write to us at toi.health1@gmail.com with 'My COVID story' in the subject lineWe will publish your experience.DISCLAIMERThe views expressed in this article should not be considered as a substitute for a physician's advice. Please consult your treating physician for more"
                content = content.replace(garbage, "")
                date = singleNewsPageHtml.find('div', {"class": "as_byline"})
                Fdate = date.find('div', attrs={'dateval': True})
                rawDate = Fdate['dateval']
                cleanDate = rawDate[8:].replace(
                    "IST", "").replace(",", "").strip()
                stdDate = datetime.strptime(
                    cleanDate, '%b %d %Y %H:%M')
                title = heading.replace('"', "").replace("\n", "")
                content = content.replace('"', "").replace("\n", "")
                cvnlp = CovidDiariesNLP()
                dataTags = cvnlp.getNLPInfo(text=content)

                data = {
                    'title': title,
                    'content': content,
                    'link': link,
                    'source': "TIMESOFINDIA",
                    'dateTime': stdDate,
                    'keywords': dataTags['keywords'],
                    'cities': dataTags['cities'],
                    'abusive': dataTags['abusive'],
                    'emotions': dataTags['emotions']
                }
                db_ref.document().set(data)
                print(f"Saved {saveCount} succesfully")
                saveCount += 1
            except Exception as e:
                return f"An Error Occured: {e}"
    return jsonify({"success": True}), 200


# Return all stories
@app.route('/', methods=['GET', 'POST'])
def read():
    if request.method == 'POST':
        order = request.json['sortByDate']
    else:
        order = 'newest'
    try:
        allStory = [doc.to_dict()
                    for doc in db_ref.order_by('dateTime').stream()]
        if order == 'newest':
            resStory = allStory[::-1]
        else:
            resStory = allStory

        return jsonify(resStory), 200

    except Exception as e:
        return f"An Error Occured: {e}"


port = int(os.environ.get('PORT', 5000))
if __name__ == '__main__':
    app.run(threaded=True, host='0.0.0.0', port=port, debug=True)
