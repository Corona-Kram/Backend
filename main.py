import math
import random
import time

import re
import os
import postgres
import psycopg2.errors as db_errors

from afinn import Afinn
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from spacy.lang.da import Danish

import logging


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
PHONE_NUMBER_EXISTS_MSG = "Phone number already registered"
with open("thankyous.txt") as filehandler:
    THANK_YOU_MSGS = [line.rstrip() for line in filehandler.readlines()]

with open("static/index.html") as fp:
    INDEX_PAGE = fp.read()

SENTIMENT_SCORER = OffensiveLanguageDetecter()
SENTIMENT_THRESHOLD = 0
PHONE_REGEX = r"(\+45|0045|) ?([\d ]*)"
WHITESPACE_REGEX = r"\s+"


db = postgres.Postgres(
    "host={} user={} password={}".format(
        os.getenv("DB_HOST", "db"),
        os.getenv("DB_USER", "postgres"),
        os.getenv("DB_PASSWORD"),
    )
)


class Receiver(BaseModel):
    phone_number: str
    timestamp: str = None


class Message(BaseModel):
    name: str = None
    text: str
    flag: bool = False
    receiver: str = None


app = FastAPI()
# app = FastAPI(openapi_prefix="/api")
# root_app.mount("/api", app)


# @root_app.get("/", response_class=HTMLResponse)
# async def root():
#     return HTMLResponse(INDEX_PAGE)



# @app.get("/hello")
# def read_root():
#     return {"Hello": "World"}


@app.post("/kram/")
def kram(message: Message):
    # empty or to long
    if not message.text or len(message.text) > SMS_CHAR_LENGTH:
        raise HTTPException(status_code=442, detail=TO_LONG_MSG_ERROR_MSG)

    # flag messages with bad scores
    msg_score = _score_message(message, SENTIMENT_THRESHOLD)
    message.flag = msg_score < SENTIMENT_THRESHOLD

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
def add_number(receiver: Receiver):
    # validate phone number
    try:
        phone_number = parse_phone_number(receiver.phone_number)
    except Exception as e:
        raise HTTPException(status_code=442, detail=INVALID_PHONE_NUMBER_MSG)

    # persist name and phone number
    try:
        timestamp = persist_phone_number(phone_number)
        if not timestamp:
            raise HTTPException(status_code=500, detail="Database error")
    except db_errors.UniqueViolation:
        raise HTTPException(status_code=409, detail=PHONE_NUMBER_EXISTS_MSG)

    phone_number.timestamp = timestamp

    return phone_number


## NOTE: Mount the files AFTER above routes
app.mount("/", StaticFiles(directory="static", html=True), name="static")



def parse_phone_number(phone_number: str) -> str:
    """
    Parse string as phone number
    """
    phone_match = re.match(PHONE_REGEX, phone_number)[2].strip()
    digits = re.sub(WHITESPACE_REGEX, "", phone_match, flags=re.UNICODE)
    
    if len(digits) == 8:
        return digits
    else:
        raise ValueError("Error parsing phone number")


def get_random_receiver() -> Receiver:
    result = db.one("SELECT phone from receivers ORDER BY random() LIMIT 1")
    return Receiver(phone_number=result)


def persist_phone_number(phone_number):
    return db.one(
        "INSERT INTO receivers (phone) VALUES(%(phone)s) RETURNING time",
        phone=phone_number,
    )


def _score_message(message: Message, threshold: int):
    try:
        sentiment_score = SENTIMENT_SCORER.score(message.text)
    except Exception as e:
        logging.warn("Error scoring sentiment {}: {}".format(message.text, e))
        sentiment_score = -math.inf

    return sentiment_score


def _persist_and_send_kram(message):
    if not message.receiver:
        message.receiver = get_random_receiver().phone_number

    db.run(
        "INSERT INTO message (name, text, receiver, flag) VALUES (%(name)s, %(text)s, %(receiver)s, %(flag)s)",
        message.dict(),
    )

    # ONLY SEND IF NOT FLAGGED
    if not message.flag:
        print("NOT FLAGGED")
        print(message)
