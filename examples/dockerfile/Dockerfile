# Sample Dockerfile with intentional hygiene issues
FROM python:latest

ENV API_TOKEN=demo-not-a-real-token
ENV APP_PORT=8080

ADD ./app /app

RUN pip install --no-cache-dir -r /app/requirements.txt

CMD ["python", "/app/main.py"]
