import json

import requests
from flask import Flask
from flask import request

app = Flask(__name__)

survey_progress = {}
questions = [
    "Do you use GR in the meetings?",
    "What are those meetings? Can you share more details?",
    "What are the interaction you do with GR in the meetings? (update data?, check and sync progress? for future planning?...)",
    "Does GR help?",
    "Why?",
]


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
        save_response_to_google_sheet(session, answer)

    return get_next_question_by_session(session)


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
