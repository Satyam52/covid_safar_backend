import datetime
import os
import random
import re
import string
from datetime import datetime
from urllib.request import Request, urlopen as uOpen

import pymongo
import requests
from bs4 import BeautifulSoup as bs
from bson.json_util import dumps
from bson.objectid import ObjectId
from flask import Flask, request, jsonify, json
from flask_cors import CORS

from covid_diaries_nlp import CovidDiariesNLP
from textFragmenter import TxtFragmenter
from utilityFunctions import cleanTitle

app = Flask(__name__)
# CORS(app, resources={r"/api/*": {"origins": "http://localhost:3000"}})

CORS(app)
# app.config['CORS_HEADERS'] = 'Content-Type'
app.config["SECRET_KEY"] = f'INSECURE_DEV_SECRET_KEY_REPLACE_STATICALLY_IN_PROD_'.join(
    random.choices(string.ascii_uppercase + string.digits, k=10))


class JSONEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, ObjectId):
            return str(o)
        return json.JSONEncoder.default(self, o)


app.json_encoder = JSONEncoder

# initialize database
try:
    dbConn = pymongo.MongoClient(
        "mongodb+srv://Abhishek:Satyam03@covid-diaries-cluster.mwtcw.mongodb.net/myFirstDatabase?retryWrites=true&w=majority")
    dbConn.server_info()
    db = dbConn['CovidDiaries']
    storyCollection = db['Stories']
    userCollection = db['users']
    print("DateBase Connected !!!")
except Exception as e:
    print(f'An Error in Database : {e}')


# scraper from slate
@app.route('/api/v1/slate', methods=['GET'])
def slate():
    # base url of corana virus tag and iterating through each page
    # print(parser.parse('2021-04-30T14:34:29+00:00'))
    allNewsLinks = []
    for i in [1, 2, 3, 4, 5]:
        newsUrl = f"https://slate.com/tag/coronavirus-diaries/{i}"
        req = Request(newsUrl, headers={'User-Agent': 'Mozilla/5.0'})
        newsPage = uOpen(req).read()
        newsPageHtml = bs(newsPage, "html.parser")
        eachNews = newsPageHtml.findAll("a", {"class": "topic-story"})

        for i in eachNews:
            tempLink = i['href']
            if tempLink not in allNewsLinks:
                allNewsLinks.append(tempLink)

    allStoryLinksInDB = []

    try:
        allStory = storyCollection.find({}, {"link": 1, "_id": 0})
        for i in allStory:
            if 'link' in i:
                allStoryLinksInDB.append(i['link'])
    except Exception as e:
        return f"link fetching error : {str(e)}", 400

    saveCount = 0
    passCount = 0

    for i in allNewsLinks:
        link = i
        if link in allStoryLinksInDB:
            print(f"pass {passCount}")
            passCount += 1
            pass
        else:
            try:
                req = requests.get(link)
                req.encoding = 'utf-8'
                singleNewsPageHtml = bs(req.text, "html.parser")
                heading = singleNewsPageHtml.find("h1",
                                                  {"article__hed"}).text
                contentHTML = singleNewsPageHtml.find_all(
                    "p", {"class": "slate-paragraph slate-graf"})  # get list of p tag
                contentText = ''
                for i in range(1, len(contentHTML) - 1):
                    contentText = contentText + contentHTML[i].text
                author = singleNewsPageHtml.find(
                    'div', {"class": "article__byline"}).text.replace("\n", "").replace("By", "").strip()
                date = singleNewsPageHtml.find(
                    'time', {"class": "article__dateline"})['content']

                cvnlp = CovidDiariesNLP()
                dataTags = cvnlp.getNLPInfo(text=contentText)
                tf = TxtFragmenter()
                paras = tf.cleanAndFragment(text=contentText)
                data = {
                    'title': cleanTitle(heading),
                    'content': paras,
                    'link': link,
                    'source': "SLATE.COM",
                    'dateTime': datetime.strptime(date[:10], "%Y-%m-%d"),
                    'keywords': dataTags['keywords'],
                    'cities': dataTags['cities'],
                    'abusive': dataTags['abusive'],
                    'emotions': dataTags['emotions'],
                    'author': author,
                    'coverage': 'global',
                    'language': "en"
                }
                storyCollection.insert_one(data)
                print(f"Saved {saveCount} succesfully")
                saveCount += 1
            except Exception as e:
                return f"An Error Occured: {e}", 400
    return jsonify({"success": True}), 200


# adding story(using scheduler)
@app.route('/api/v1/toi', methods=['GET'])
def toi():
    searchString = 'my-covid-story'  # can have list of keywords
    # searchString = request.json['content']   #if we want to search custom string via front end

    newsUrl = "https://timesofindia.indiatimes.com/life-style/health-fitness/" + \
              searchString.strip()
    req = Request(newsUrl, headers={'User-Agent': 'Mozilla/5.0'})
    newsPage = uOpen(req).read()
    newsPageHtml = bs(newsPage, "html.parser")
    eachNews = newsPageHtml.findAll("span", {"class": "md_news_leftin"})
    allNewsLinks = []

    for i in eachNews:
        tempLink = i.a['href']
        if tempLink not in allNewsLinks:
            allNewsLinks.append(i.a['href'])

    # checking curated page 1 and 2
    for i in [1, 2, 3]:
        newsUrl = f"https://timesofindia.indiatimes.com/etimeslistgenric.cms?msid=2886704&query=mycoronastory&datasection=lifestyle&curpg={i}"
        req = Request(newsUrl, headers={'User-Agent': 'Mozilla/5.0'})
        newsPage = uOpen(req).read()
        newsPageHtml = bs(newsPage, "html.parser")
        eachNews = newsPageHtml.findAll("span", {"class": "md_news_left"})

        for i in eachNews:
            tempLink = i.a['href']
            if tempLink not in allNewsLinks:
                allNewsLinks.append(i.a['href'])

    allStoryLinksInDB = []

    try:
        allStory = storyCollection.find({}, {"link": 1, "_id": 0})
    except Exception as e:
        return f"link fetching error : {e}", 400

    for i in allStory:
        allStoryLinksInDB.append(i['link'])

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
                contentHTML = singleNewsPageHtml.find(
                    "div", {"class": "Normal"})
                contentText = contentHTML.text
                garbageTextArray = ['Did you fight COVID-19?', 'We want to hear all about it.',
                                    'ETimes Lifestyle is calling all the survivors of COVID to share their stories of survival and hope.',
                                    "Write to us at toi.health1@gmail.com with 'My COVID story' in the subject lineWe will publish your experience.",
                                    "DISCLAIMERThe views expressed in this article should not be considered as a substitute for a physician's advice.",
                                    "Please consult your treating physician for more details."
                                    ]
                for i in garbageTextArray:
                    contentText = contentText.replace(i, "")
                date = singleNewsPageHtml.find('div', {"class": "as_byline"})
                Fdate = date.find('div', attrs={'dateval': True})
                rawDate = Fdate['dateval']
                cleanDate = rawDate[8:].replace(
                    "IST", "").replace(",", "").strip()
                stdDate = datetime.strptime(
                    cleanDate, '%b %d %Y %H:%M')
                contentText = contentText.replace('"', "").replace("\n", "")
                cvnlp = CovidDiariesNLP()
                dataTags = cvnlp.getNLPInfo(text=contentText)
                tf = TxtFragmenter()
                paras = tf.cleanAndFragment(text=contentText)

                data = {
                    'title': cleanTitle(heading),
                    'content': paras,
                    'link': link,
                    'source': "TOI",
                    'dateTime': stdDate,
                    'keywords': dataTags['keywords'],
                    'cities': dataTags['cities'],
                    'abusive': dataTags['abusive'],
                    'emotions': dataTags['emotions'],
                    'coverage': 'india',
                    'language': "en"
                }
                storyCollection.insert_one(data)
                print(f"Saved {saveCount} succesfully")
                saveCount += 1
            except Exception as e:
                print(f"An Error Occured: {e}")
    return ("Successfully scraped"), 200


# search string
PER_PAGE = 9


@app.route('/api/v1/', methods=['GET'])
def getStory():
    order = request.args.get('date') or 'newest'
    page = int(request.args.get('page', 1))
    coverage = request.args.get('coverage') or 'global'
    searchString = request.args.get('search')
    lang = request.args.get('language') or 'en'

    if lang == 'null':
        lang = 'en'

    if searchString:
        regex = re.compile(searchString, re.IGNORECASE)
        if coverage == 'global':
            query = {'language': lang, "$or": [{"content": {"$regex": regex}}, {"title": {"$regex": regex}}]}
        else:
            query = {'coverage': coverage,
                     'language': lang, "$or": [{"content": {"$regex": regex}}, {"title": {"$regex": regex}}]}
    else:
        if coverage == 'global':
            query = {'language': lang}
        else:
            query = {'coverage': coverage, 'language': lang}

    try:
        totalFilteredCount = storyCollection.count_documents(query)
        if order == 'newest':
            filteredStory = storyCollection.find(query,
                                                 {'title': 1, "emotions": 1, "keywords": 1, "source": 1, "link": 1,
                                                  "dateTime": 1, "cities": 1}).sort(
                [('dateTime', pymongo.DESCENDING)]).skip(PER_PAGE * (page - 1)).limit(PER_PAGE)
        else:
            filteredStory = storyCollection.find(query,
                                                 {'title': 1, "emotions": 1, "keywords": 1, "source": 1, "link": 1,
                                                  "dateTime": 1, "cities": 1}).sort(
                [('dateTime', pymongo.ASCENDING)]).skip(PER_PAGE * (page - 1)).limit(PER_PAGE)

        #  returning 9 stories per page
        resStories = [{"count": totalFilteredCount}]
        for i in filteredStory:
            resStories.append(i)
            # print(resStory)
        return jsonify(resStories), 200
        #     return jsonify({"message":"success"}),200
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route('/api/v1/id=<_id>', methods=['GET'])
def story(_id):
    # id = request.args.get('id')
    if _id in (None, ''):
        return f"Article Id not found", 400
    try:
        storyFind = storyCollection.find_one({'_id': ObjectId(_id)})
        if not storyFind:
            return f"Article not found", 404
        return dumps(storyFind), 200

    except Exception as e:
        return f"An Error Occured: {e}"


# def run_task():
#     schedule.every().day.at("09:03:50").do(toi)
#     schedule.every().day.at("00:00").do(slate)
#     while True:
#         schedule.run_pending()
#         time.sleep(1)


port = int(os.environ.get('PORT', 5000))
if __name__ == '__main__':
    # try:
    #     threading.Thread(target=run_task).start()
    # except Exception as e:
    #     print("Caught an exception", e)

    # threading.Thread(target=run_task).start()
    app.run(threaded=True, host='0.0.0.0', port=port, debug=True)
