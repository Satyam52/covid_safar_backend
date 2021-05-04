import pke
import json
import requests
import text2emotion as te
from profanity_check import predict, predict_prob
from flashtext import KeywordProcessor
from collections import Counter


# Prepare keyword processor to extract cities list
cities_list = []
with open('cities.json', 'r') as j:
    for city in json.loads(j.read()):
        cities_list.append(city['city'])
keyword_processor = KeywordProcessor()
keyword_processor.add_keywords_from_list(cities_list)


class CovidDiariesNLP:
    def __init__(self):
        pass

    def getNLPInfo(self, text):
        return {
            'keywords': self.__getKeywords__(text),
            'cities': self.__getCitiesInDoc__(text),
            'abusive': self.__getProfanityValue__(text),
            'emotions': self.__getEmotions__(text)
        }

    def __getKeywords__(self, doc):
        try:
            # initialize keyphrase extraction model, here TopicRank
            extractor = pke.unsupervised.TopicRank()

            # load the content of the document, here document is expected to be in raw
            # format (i.e. a simple text file) and preprocessing is carried out using spacy
            extractor.load_document(input=doc, language='en')

            # keyphrase candidate selection, in the case of TopicRank: sequences of nouns
            # and adjectives (i.e. `(Noun|Adj)*`)
            extractor.candidate_selection()

            # candidate weighting, in the case of TopicRank: using a random walk algorithm
            extractor.candidate_weighting()

            # N-best selection, keyphrases contains the 10 highest scored candidates as
            # (keyphrase, score) tuples
            keyphrases = extractor.get_n_best(n=10)

            return [kw for kw, sc in keyphrases]
        except:
            return []

    def __getProfanityValue__(self, doc):
        try:
            return predict_prob([doc])[0]
        except:
            return None

    def __getCitiesInDoc__(self, doc):
        try:
            cities_in_article = keyword_processor.extract_keywords(doc)
            return list(set(cities_in_article))
        except:
            return []

    def __getEmotions__(self, doc):
        try:
            emos = te.get_emotion(doc)
            mostCommonEmos = Counter(emos).most_common(2)
            return [e for e, prob in mostCommonEmos]
        except:
            return []
