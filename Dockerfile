FROM python:3.9-alpine
RUN apk add build-base
WORKDIR /app
COPY . .
RUN pip install --no-cache-dir pipenv && \
    pipenv install --deploy --clear
ENTRYPOINT ["pipenv", "run", "python3", "main.py"]