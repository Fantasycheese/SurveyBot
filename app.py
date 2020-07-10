import json
import pickle

import requests
import nltk
import numpy as np
import pandas as pd
from flask import Flask
from flask import request
from threading import Thread
from sklearn.feature_extraction.text import TfidfVectorizer
from nltk.corpus import stopwords

app = Flask(__name__)

survey_progress = {}
questions = [
    "Do you use GR in the meetings?",
    "What are those meetings? Can you share more details?",
    "What are the interaction you do with GR in the meetings? (update data?, check and sync progress? for future planning?...)",
    "Does GR help?",
    "Why?",
    "How often do you update the KRs on google sheet?",
    "When do you update KRs?  What makes or motivate you to update KRs?",
    "What do you find most frustrating about using google sheet? (anything, for data input, collabration...)",
    "What do you find the best about using google sheet?",
    "how does GR compare to google sheet ?"
]

nltk.download('stopwords')
english_stopwords = stopwords.words('english')
unigrams_vectorizer = TfidfVectorizer(stop_words=english_stopwords, ngram_range=(1, 1))
bigrams_vectorizer = TfidfVectorizer(stop_words=english_stopwords, ngram_range=(2, 2), min_df=2)


@app.route('/')
def home():
    return 'Hello Flask'


@app.route('/get-next-question', methods=['POST'])
def get_next_question():
    body = request.get_json()
    session = body["session"]
    if session not in survey_progress:
        survey_progress[session] = 0
    else:
        answer = body["queryResult"]["queryText"]
        id = body["responseId"]
        Thread(target=save_response_to_google_sheet, args=(session, answer)).start()
        Thread(target=tf_idf_fit, args=(id, answer)).start()

    return get_next_question_by_session(session)


@app.route('/get-top-words', methods=['post'])
def get_top_words():
    with open("tf_idf_model.pickle", "rb") as f:
        vectorizer = pickle.load(f)

    top_n = 10
    text = ' '.join(request.get_json()["texts"])
    embedding = vectorizer.transform([text])[0]
    sorted_nzs = np.argsort(embedding.data)[:-(top_n + 1):-1]
    feature_names = np.array(vectorizer.get_feature_names())
    words = feature_names[embedding.indices[sorted_nzs]]
    scores = embedding.data[sorted_nzs]
    return dict(zip(words, scores))


def save_response_to_google_sheet(session: str, answer: str):
    question = f"Q{survey_progress[session]}"
    requests.post(f"https://script.google.com/macros/s/AKfycbxU74OfKZ14G2I2LM3xLezCNgPnrcIxEAn4crFLqxsEIeiCN8U/exec?session={session}&question={question}&answer={answer}")


def get_next_question_by_session(session: str):
    if survey_progress[session] == len(questions):
        response = "Thanks!"
    else:
        response = questions[survey_progress[session]]
        survey_progress[session] += 1
    return json.dumps({
        "fulfillmentMessages": [
            {
                "text": {
                    "text": [
                        response
                    ]
                }
            }
        ]
    })


def tf_idf_fit(id, answer):
    print(f"training for new response: {answer}")
    corpus = pd.read_csv('corpus.csv', index_col='id')
    corpus.loc[id] = [answer]
    corpus.to_csv('corpus.csv')
    # unigrams_vectorizer.fit(corpus)
    #
    # if len(corpus.answer) > 1:
    #     bigrams_vectorizer.fit(corpus)
    #
    # vocabulary = {**unigrams_vectorizer.vocabulary_, **bigrams_vectorizer.vocabulary_}
    # ngram_dict = {word: index for index, word in enumerate(vocabulary.keys())}

    # vectorizer = TfidfVectorizer(stop_words=english_stopwords, vocabulary=ngram_dict, ngram_range=(1, 2))

    vectorizer = TfidfVectorizer(stop_words=english_stopwords, ngram_range=(1, 1))
    vectorizer.fit(corpus)

    with open("tf_idf_model.pickle", "wb") as f:
        pickle.dump(vectorizer, f)

    print(f"training for new response completed: {answer}")


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
