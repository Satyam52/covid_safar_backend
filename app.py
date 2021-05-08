from flask import Flask, render_template, url_for, request, redirect, jsonify, json
import requests
import datetime
from datetime import datetime
from bs4 import BeautifulSoup as bs
from urllib.request import Request, urlopen as uOpen
from bson.json_util import dumps
from bson.objectid import ObjectId
import os
from firebase_admin import credentials, firestore, initialize_app
from flask_cors import CORS
from covid_diaries_nlp import CovidDiariesNLP
import pymongo

app = Flask(__name__)
CORS(app)

# initialize database
try:
    dbConn = pymongo.MongoClient(
        "mongodb+srv://Abhishek:Satyam03@covid-diaries-cluster.mwtcw.mongodb.net/<dbname>?retryWrites=true&w=majority")
    dbConn.server_info()
    db = dbConn['Stories']
    collection = db['StoriesCollection']
    print("DateBase Connected !!!")
except Exception as e:
    print(f'An Error in Database : {e}')


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

    # checking curated page 1 and 2
    for i in [1, 2]:
        newsUrl = f"https://timesofindia.indiatimes.com/etimeslistgenric.cms?msid=2886704&query=mycoronastory&datasection=lifestyle&curpg={i}"
        req = Request(newsUrl, headers={'User-Agent': 'Mozilla/5.0'})
        newsPage = uOpen(req).read()
        newsPageHtml = bs(newsPage, "html.parser")
        eachNews = newsPageHtml.findAll("span", {"class": "md_news_left"})

        for i in eachNews:
            allNewsLinks.append(i.a['href'])

    allStoryLinksInDB = []

    try:
        allStory = collection.find({}, {"link": 1, "_id": 0})
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
                garbageText = "Did you fight COVID-19? We want to hear all about it. ETimes Lifestyle is calling all the survivors of COVID to share their stories of survival and hope.Write to us at toi.health1@gmail.com with 'My COVID story' in the subject lineWe will publish your experience.DISCLAIMERThe views expressed in this article should not be considered as a substitute for a physician's advice. Please consult your treating physician for more"
                contentText = contentText.replace(garbageText, "")
                date = singleNewsPageHtml.find('div', {"class": "as_byline"})
                Fdate = date.find('div', attrs={'dateval': True})
                rawDate = Fdate['dateval']
                cleanDate = rawDate[8:].replace(
                    "IST", "").replace(",", "").strip()
                stdDate = datetime.strptime(
                    cleanDate, '%b %d %Y %H:%M')
                title = heading.replace('"', "").replace("\n", "")
                contentText = contentText.replace('"', "").replace("\n", "")
                cvnlp = CovidDiariesNLP()
                dataTags = cvnlp.getNLPInfo(text=contentText)
                # garbageHTML = """ <strong><em>Did you fight COVID-19? We want to hear all about it. ETimes Lifestyle is calling all the survivors of COVID to share their stories of survival and hope.<div class="last7brdiv"></div><br/><div class="last6brdiv"></div><br/>Write to us at toi.health1@gmail.com with 'My COVID story' in the subject line<div class="last5brdiv"></div><br/><div class="top2brdiv"></div><br/>We will publish your experience.<div class="last3brdiv"></div><br/>DISCLAIMER<div class="last1brdiv"></div><br/><br/>The views expressed in this article should not be considered as a substitute for a physician's advice. Please consult your treating physician for more details.</em></strong>"""
                # garbage = bs(garbageHTML, 'html.parser')
                strongTags = contentHTML.find_all('strong')
                try:
                    strongTags[1].decompose()
                except Exception as e:
                    print(e)
                # contentHTML = contentHTML.strongTags[1]
                # print(contentHTML)
                contentHTML = str(contentHTML).replace(
                    '<br>', "<br/>")
                data = {
                    'title': title,
                    'content': contentHTML,
                    'link': link,
                    'source': "TIMESOFINDIA",
                    'dateTime': stdDate,
                    'keywords': dataTags['keywords'],
                    'cities': dataTags['cities'],
                    'abusive': dataTags['abusive'],
                    'emotions': dataTags['emotions']
                }
                collection.insert_one(data)
                print(f"Saved {saveCount} succesfully")
                saveCount += 1
            except Exception as e:
                return f"An Error Occured: {e}"
    return jsonify({"success": True}), 200


# total count stories for pagination
@app.route("/paginate", methods=["GET"])
def pagination():
    try:
        totalArticleCount = collection.estimated_document_count()
        return jsonify({"totalArticleCount": totalArticleCount}), 200

    except Exception as e:
        return f"An Error Occured: {e}"


# Return all stories
PER_PAGE = 10
@app.route('/', methods=['GET'])
def readAll():
    order = request.args.get('date', 'newest')
    page = int(request.args.get('pg', 1))

    try:
        totalArticleCount = collection.estimated_document_count()
        if order == 'newest':
            allStory = collection.find().sort(
                [('dateTime', pymongo.DESCENDING)]).skip(PER_PAGE*(page-1)).limit(PER_PAGE)
        else:
            allStory = collection.find().sort(
                [('dateTime', pymongo.ASCENDING)]).skip(PER_PAGE*(page-1)).limit(PER_PAGE)

        # # returning 10 stories per page
        resStory = []
        # resStory = resStory[(page-1)*PER_PAGE:page*PER_PAGE]
        for i in allStory:
            resStory.append(i)
        # print(resStory)
        return dumps(resStory), 200

    except Exception as e:
        return f"An Error Occured: {e}"


# Return single story by id
@app.route('/id=<_id>', methods=['GET'])
def story(_id):
    # id = request.args.get('id')
    if _id in (None, ''):
        return f"Article Id not found", 400
    try:
        story = collection.find_one({'_id': ObjectId(_id)})
        if not story:
            return f"Article not found", 404

        return dumps(story), 200

    except Exception as e:
        return f"An Error Occured: {e}"


port = int(os.environ.get('PORT', 5000))
if __name__ == '__main__':
    app.run(threaded=True, host='0.0.0.0', port=port, debug=True)
