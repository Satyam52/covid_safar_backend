import re


class TxtFragmenter:
    def __init__(self):
        pass

    def __fragment(self, text):
        textList = text.split('.')
        chunk = []
        fragments = []
        temp = ''
        for t in textList:
            if len(temp + ('.' + t)) < 740:
                temp += ('.' + t)
            else:
                chunk.append(temp)
                temp = ''
        chunk.append(temp)
        for c in chunk:
            fragments.append(c[1:] + '.')
        return fragments

    def __cleanText(self, text):
        text = re.sub('\.+', '.', text)
        text = re.sub('\ - ', ' ', text)
        return text

    def cleanAndFragment(self, text):
        text = self.__cleanText(text)
        return self.__fragment(text)
