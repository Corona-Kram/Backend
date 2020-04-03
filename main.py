import math
import random
import time

from afinn import Afinn
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from spacy.lang.da import Danish


class OffensiveLanguageDetecter:
    def __init__(self):
        self.nlp = Danish()
        self.sentiment_cls = Afinn(language="da")

    def score(self, message):
        tokenized_msg = " ".join(t.text for t in self.nlp(message))
        return self.sentiment_cls.score(tokenized_msg)


################################################################################


SMS_CHAR_LENGTH = 160
TO_LONG_MSG_ERROR_MSG = "Message to long"
INVALID_PHONE_NUMBER_MSG = "Invalid phone number."
with open("static/thankyous.txt") as filehandler:
    THANK_YOU_MSGS = [line.rstrip() for line in filehandler.readlines()]

SENTIMENT_SCORER = OffensiveLanguageDetecter()
SENTIMENT_THRESHOLD = 1


class Message(BaseModel):
    name: str
    text: str
    timestamp: int = None


class Receiver(BaseModel):
    name: str
    phone_number: str
    timestamp: int = None


app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/", response_class=HTMLResponse)
async def root():
    return """
    <html>
        <head>
            <title>Some HTML in here</title>
        </head>
        <body>
            <h1>Look ma! HTML!</h1>
        </body>
    </html>
    """


@app.get("/hello")
def read_root():
    return {"Hello": "World"}


@app.post("/kram/")
def kram(message: Message):
    # empty or to long
    if not message.text or len(message.text) > SMS_CHAR_LENGTH:
        raise HTTPException(status_code=442, detail=TO_LONG_MSG_ERROR_MSG)

    # only accept message full of happy words
    msg_score = _score_message(message, SENTIMENT_THRESHOLD)
    if msg_score < SENTIMENT_THRESHOLD:
        raise HTTPException(status_code=442, detail="Nope. Not positive enough.")

    # save it / send it off
    success = _persist_and_send_kram(message)
    if not success:
        raise HTTPException(status_code=500, detail="Database error")

    return {
        "message": message.text,
        "len": len(message.text),
        "sentiment_score": msg_score,
        "thank_you_msg": random.choice(THANK_YOU_MSGS),
    }


@app.post("/add_number/")
def add_number(phone_number: Receiver):
    # validate phone number
    try:
        phone_number = parse_phone_number(phone_number)
    except:
        raise HTTPException(status_code=442, detail=TO_LONG_MSG_ERROR_MSG)

    # persist name and phone number
    timestamp = persist_phone_number(phone_number)
    if not timestamp:
        raise HTTPException(status_code=500, detail="Database error")

    phone_number.timestamp = timestamp

    return phone_number


def parse_phone_number(phone_number: str) -> str:
    """
    Parse string as phone number

    NOTE:
        - For the time being we assume the string is a valid phone number.
    """
    return phone_number


def persist_phone_number(phone_number):
    """
    TODO:
        - Persist phone number to database.
        - Return timestamp from database, or None if failed.
    """
    return time.time()


def _score_message(message: Message, threshold: int):
    try:
        sentiment_score = SENTIMENT_SCORER.score(message.text)
    except:
        sentiment_score = -math.inf

    return sentiment_score


def _persist_and_send_kram(message):
    # database stuff
    return True
