FROM python:alpine3.10

RUN pip install requests mcstatus pymongo
WORKDIR /app
COPY client.py .

ENTRYPOINT ["python", "/app/client.py"]