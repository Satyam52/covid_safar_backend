import random

counts = {
    'flower': 10,
    'gloves': 3,
    'handwash': 5,
    'mask': 8,
    'mountain': 9,
    'oxygen': 4,
    'sanitizer': 5,
    'socialdistancing': 6,
    'trees': 10,
    'vaccine': 11,
    'virus': 9,
    'water': 10
}


def getImageByKeywords(keys, no_of_images):
    res = []
    c = 0
    for k in keys:
        if (c < no_of_images):
            if k in ['covid', 'covid-19', 'virus']:
                res.append('./pictures/virus' + str(random.randint(1, counts['virus'])))
                c += 1
            elif k in ['oxygen', 'breath', 'respiratory', 'chest']:
                res.append('./pictures/oxygen' + str(random.randint(1, counts['oxygen'])))
                c += 1
            elif k in ['sanitize', 'wash', 'hand']:
                res.append('./pictures/handwash' + str(random.randint(1, counts['handwash'])))
                c += 1
            elif k in ['social', 'distance']:
                res.append('./pictures/socialdistancing' + str(random.randint(1, counts['socialdistancing'])))
                c += 1
            elif k in ['vaccine', 'medical', 'cure', 'prevent']:
                res.append('./pictures/vaccine' + str(random.randint(1, counts['vaccine'])))
                c += 1
            elif k in ['death', 'die', 'died']:
                res.append('./pictures/flower' + str(random.randint(1, counts['flower'])))
                c += 1
            else:
                i = random.choice(['mountain', 'trees', 'water'])
                res.append('./pictures/' + i + str(random.randint(1, counts[i])))
                c += 1
        else:
            break
    if (c < no_of_images):
        return res + res[:no_of_images - c]
    else:
        return res
