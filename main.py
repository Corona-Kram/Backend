import math
import random
import time

import re
import os
import postgres
import psycopg2.errors as db_errors
import requests

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
SMS_GATEWAY_URL = "https://mm.inmobile.dk/Api/V2/SendMessages"
SMS_API_KEY = os.getenv("SMS_API_KEY")
SMS_TEMPLATE_ANONYMOUS = "Fra CoronaKram.dk:\n{}"
SMS_TEMPLATE_NAMED = "\n{} via CoronaKram.dk:\n{}"


SMS_SEND_TEMPLATE = """<request>
    <authentication apikey="{}" />
    <data>
        <message>
            <sendername>CoronaKram</sendername>
            <text encoding="utf-8"><![CDATA[{}]]></text>
            <recipients>
                <msisdn>45{}</msisdn>
            </recipients>
        </message>
    </data>
</request>"""

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


# @app.get("/hello")
# def read_root():
#     return {"Hello": "World"}


@app.post("/kram/")
def kram(message: Message):
    # empty or to long
    if not message.text or len(message.text) > SMS_CHAR_LENGTH:
        raise HTTPException(status_code=442, detail=TO_LONG_MSG_ERROR_MSG)

    try:
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
    except Exception as e:
        logging.error(e)


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

    receiver.timestamp = timestamp

    return receiver


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
    # Get a phone number from a receiver that has NOT received anything in the last 10 minutes
    result = db.one(
        "SELECT phone from receivers WHERE last_sent < (now() - interval '30 minutes') ORDER BY random() LIMIT 1"
    )
    # This might not produce results (None)
    if not result:
        return result
    # Update sent timestamp
    db.run(
        "UPDATE receivers SET last_sent = now() WHERE phone = %(phone)s", phone=result
    )
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
        message.receiver = get_random_receiver()

    db.run(
        "INSERT INTO message (name, text, receiver, flag) VALUES (%(name)s, %(text)s, %(receiver)s, %(flag)s)",
        message.dict(),
    )

    # ONLY SEND IF NOT FLAGGED AND HAS A RECEIVER
    if not message.flag and message.receiver:
        try:
            sms_body = _sms_body(message)
            requests.post(SMS_GATEWAY_URL, data={"xml": sms_body})
            return True
        except Exception as e:
            logging.error("Error sending: {}".format(e))
            return False
    else:
        # Return True if the message was flagged; user should not be notified
        return True


def _sms_body(message):
    # Truncate text to ~50 characters
    message.text = message.text[:50]

    if message.name:
        content = SMS_TEMPLATE_NAMED.format(message.name, message.text)
    else:
        content = SMS_TEMPLATE_ANONYMOUS.format(message.text)

    return SMS_SEND_TEMPLATE.format(SMS_API_KEY, content, message.receiver)
