import random
import time

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

SMS_CHAR_LENGTH = 160
TO_LONG_MSG_ERROR_MSG = "Message to long"
INVALID_PHONE_NUMBER_MSG = "Invalid phone number."
with open("static/thankyous.txt") as filehandler:
    THANK_YOU_MSGS = [line.rstrip() for line in filehandler.readlines()]


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
def send_kram(message: Message):
    print(message)
    if len(message.text) > SMS_CHAR_LENGTH:
        raise HTTPException(status_code=442, detail=TO_LONG_MSG_ERROR_MSG)

    return {
        "message": message.text,
        "len": len(message.text),
        "thank_you_msg": random.choice(THANK_YOU_MSGS),
    }


@app.post("/add_number/")
def add_number(phone_number: Receiver):
    try:
        phone_number = parse_phone_number(phone_number)
    except:
        raise HTTPException(status_code=442, detail=TO_LONG_MSG_ERROR_MSG)

    success = persist_phone_number(phone_number)

    if not success:
        raise HTTPException(status_code=500, detail="Database error")

    phone_number.timestamp = time.time()

    return phone_number  # {"phone-number": phone_number, "success": success}


def parse_phone_number(phone_number: str) -> str:
    """
    Parse string as phone number

    NOTE:
        For the time being we assume the string is a valid phone number.
    """
    return phone_number


def persist_phone_number(phone_number):
    """TODO: Persist phone number to database or sum'in"""
    return True
