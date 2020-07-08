import json

from flask import Flask
from flask import request

app = Flask(__name__)

sessions = {}
questions = [
    "Do you use GR in the meetings?",
    "What are those meetings? Can you share more details?",
    "What are the interaction you do with GR in the meetings? (update data?, check and sync progress? for future planning?...)"
    "Does GR help?"
    "Why?"
]


@app.route('/')
def home():
    return 'Hello Flask'


@app.route('/get-next-question', methods=['POST'])
def get_next_question():
    body = request.get_json()
    session = body["session"]
    if session not in sessions:
        sessions[session] = len(questions)-1
    if sessions[session] < 0:
        response = "Thanks!"
    else:
        response = questions[sessions[session]]
        sessions[session] -= 1

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
