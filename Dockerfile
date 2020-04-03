FROM python:slim 

RUN pip install aiofiles uvicorn fastapi psycopg2-binary postgres afinn spacy

ADD . .

EXPOSE 80

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "80"]] 
