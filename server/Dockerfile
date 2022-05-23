FROM python:alpine3.10

RUN pip install ipaddress fastapi uvicorn pydantic
WORKDIR /app
COPY server.py .

ENTRYPOINT ["uvicorn", "server:app", "--host", "0.0.0.0"]