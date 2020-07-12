import json
import pickle

import requests
import nltk
import numpy as np
import pandas as pd
from flask import Flask, request, render_template
from threading import Thread
from sklearn.feature_extraction.text import TfidfVectorizer
from nltk.corpus import stopwords

app = Flask(__name__)

survey_progress = {}

db = requests.get("https://script.google.com/macros/s/AKfycbxU74OfKZ14G2I2LM3xLezCNgPnrcIxEAn4crFLqxsEIeiCN8U/exec").json()
questionIds = db[0][1:]
questions = db[1][1:]

nltk.download('stopwords')
english_stopwords = stopwords.words('english')
unigrams_vectorizer = TfidfVectorizer(stop_words=english_stopwords, ngram_range=(1, 1))
bigrams_vectorizer = TfidfVectorizer(stop_words=english_stopwords, ngram_range=(2, 2), min_df=2)


@app.route('/')
def home():
    return render_template('index.html')


@app.route('/get-next-question', methods=['POST'])
def get_next_question():
    body = request.get_json()
    session = body["session"]
    if session not in survey_progress:
        survey_progress[session] = 0
    else:
        id = body["responseId"]
        answer = body["queryResult"]["queryText"]
        Thread(target=tf_idf, args=(session, survey_progress[session], id, answer)).start()

    return get_next_question_by_session(session)


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


def tf_idf(session, progress, id, answer):
    print(f"{id}: saving response to google sheet...")
    questionId = questionIds[progress-1]
    saveResponse = requests.post(f"https://script.google.com/macros/s/AKfycbxU74OfKZ14G2I2LM3xLezCNgPnrcIxEAn4crFLqxsEIeiCN8U/exec?session={session}&question={questionId}&answer={answer}")
    if saveResponse.status_code != 200:
        return

    print(f"{id}: getting corpus from google sheet...")
    table = requests.get("https://script.google.com/macros/s/AKfycbxU74OfKZ14G2I2LM3xLezCNgPnrcIxEAn4crFLqxsEIeiCN8U/exec").json()
    df = pd.DataFrame(table)
    corpus = df.drop([0, 1, 2]).drop(0, 1).applymap(str).apply(' '.join, axis=1).to_list()

    print(f"{id}: training with new corpus...")

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

    print(f"{id}: updating tf-idf scores...")
    text = ' '.join(df[progress].drop([0, 1, 2]))
    top_words = get_top_words(vectorizer, text)
    session = 'TF_IDF'
    answer = ', '.join(top_words)
    requests.post(f"https://script.google.com/macros/s/AKfycbxU74OfKZ14G2I2LM3xLezCNgPnrcIxEAn4crFLqxsEIeiCN8U/exec?session={session}&question={questionId}&answer={answer}")


def get_top_words(vectorizer: TfidfVectorizer, text: str):
    top_n = 10
    embedding = vectorizer.transform([text])[0]
    sorted_nzs = np.argsort(embedding.data)[:-(top_n + 1):-1]
    feature_names = np.array(vectorizer.get_feature_names())
    words = feature_names[embedding.indices[sorted_nzs]]
    scores = embedding.data[sorted_nzs]
    return dict(zip(words, scores))


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
