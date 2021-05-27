@app.route('/private/addStory', methods=['POST'])
def addStory():
    request_data = request.get_json()
    token = request_data['token']
    try:
        id_info = id_token.verify_oauth2_token(
            token, grequests.Request(), os.getenv("G_CLIENT_SECRET"))

        errorMsg = []  # this will collect all the errors while processing form

        if id_info:  # if user in token

            storyObj = dict()  # populating storyObj with data from frontend
            storyObj['gmail'] = id_info['email']
            storyObj['title'] = request_data['title'] if 'title' in request_data else errorMsg.append(
                {"message": "title is required"})
            storyObj['author'] = request_data['author'] if 'author' in request_data else errorMsg.append(
                {"message": "Author is required"})
            storyObj['dateTime'] = request_data['dateTime'] if 'dateTime' in request_data else errorMsg.append(
                {"message": "date is required"})
            storyObj['gender'] = request_data['gender'] if 'gender' in request_data else errorMsg.append(
                {"message": "gender is required"})
            storyObj['audience'] = request_data['audience'] if 'audience' in request_data else errorMsg.append(
                {"message": "Audience type is required"})

            # checking for duplicate title in database
            findExperienceInDB = storyCollection.find_one({'title': storyObj['title']})
            if findExperienceInDB:
                return jsonify(
                    {"isSaved": False, "error": [{"message": "This title already exist.Please choose another"}]}), 400

            tf = TxtFragmenter()
            if 'content' in request_data:
                paras = tf.cleanAndFragment(text=request_data['content'])
            storyObj['content'] = paras if 'content' in request_data and len(paras) > 0 else errorMsg.append(
                {"message": "content is required"})

            if len(errorMsg) > 0:  # error after processing the formData
                return jsonify({'isSaved': False, "error": errorMsg}), 400

            cvnlp = CovidDiariesNLP()
            dataTags = cvnlp.getNLPInfo(text=request_data['content'])
            if dataTags:
                storyObj['keywords'] = dataTags['keywords']
                storyObj['cities'] = dataTags['cities']
                storyObj['abusive'] = dataTags['abusive']
                storyObj['emotions'] = dataTags['emotions']

            try:  # handle databases carefully
                storyCollection.insert_one(storyObj)
                _id = storyObj["_id"]
                newStoriesIdInUser = {'$addToSet': {"storiesId": {"_id": _id}}}
                userCollection.update_one({"gmail": id_info['email']}, newStoriesIdInUser)
            except Exception as exc:
                return jsonify({"isSaved": False, "error": str(exc)}), 400

            return jsonify({"isSaved": True,
                            "success": [{'message': "Successfully submitted"}]
                            }), 200
        else:
            return jsonify({"isSaved": False,
                            "error": [{"message": 'Not signed in'}]
                            }), 404
    except ValueError as e:
        # Invalid token
        return jsonify({"isSaved": False,
                        "error": [{"message": 'Not signed in'}, {"message": str(e)}]
                        }), 404


@app.route('/private/edit/id=<_id>', methods=['POST'])
def editStory(_id):
    if _id in (None, ''):
        return jsonify({"error": [{"message": "experience not found"}]}), 400

    request_data = request.get_json()
    token = request_data['token']
    try:
        id_info = id_token.verify_oauth2_token(
            token, grequests.Request(), os.getenv("G_CLIENT_SECRET"))

        searchExperience = storyCollection.find_one({"_id": ObjectId(_id)})

        if id_info and id_info['email'] == searchExperience['gmail']:

            errorMsg = []  # this will collect all the errors while processing form

            # populating title and content with data from frontend
            newTitle = request_data['title'] if 'title' in request_data else errorMsg.append(
                {"message": "title is required"})
            newContent = request_data['content'] if 'content' in request_data else errorMsg.append(
                {"message": "Content is required"})

            if len(errorMsg) > 0:  # error after processing the formData
                return jsonify({'isSaved': False, "error": errorMsg}), 400

            if newTitle != searchExperience['title']:
                # checking for duplicate title in database
                findExperienceInDB = storyCollection.find_one({'title': newTitle}, {'title': 1})
                if findExperienceInDB:
                    return jsonify(
                        {"isSaved": False,
                         "error": [{"message": "This title already exist.Please choose another"}]}), 400

            tf = TxtFragmenter()
            paras = tf.cleanAndFragment(text=newContent)
            newContent = paras

            if newTitle == searchExperience['title']:
                if newContent == searchExperience['content']:
                    return jsonify(
                        {"isSaved": True,
                         "error": [{"message": "No changes made"}]}), 200

            cvNlp = CovidDiariesNLP()
            dataTags = cvNlp.getNLPInfo(text=request_data['content'])
            newKeywords = dataTags['keywords']
            newCities = dataTags['cities']
            newAbusive = dataTags['abusive']
            newEmotions = dataTags['emotions']

            try:  # handle databases carefully
                newStoryQuery = {'$set': {'title': newTitle, 'content': newContent,
                                          'keywords': newKeywords, 'cities': newCities,
                                          'abusive': newAbusive, 'emotions': newEmotions}}
                storyCollection.update_one(searchExperience, newStoryQuery, True)
            except Exception as exc:
                return jsonify({"isSaved": False, "error": [{"message": str(exc)}]}), 400

            return jsonify({"isSaved": True,
                            "success": [{'message': "Successfully submitted"}]
                            }), 200
        else:
            return jsonify({"isSaved": False,
                            "error": [{"message": 'Not signed in'}]
                            }), 404
    except ValueError as e:
        # Invalid token
        return jsonify({"isSaved": False,
                        "error": [{"message": 'Not signed in'}, {"message": str(e)}]
                        }), 404
