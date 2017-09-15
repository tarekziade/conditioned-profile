# Servicebook
FROM python:3.6-slim

RUN apt-get update
RUN apt-get install -y git build-essential make libssl-dev libffi-dev python3-dev python3-venv wget libgtk-3-dev libX11-xcb-dev libXt-dev

WORKDIR /app

RUN wget https://github.com/mozilla/geckodriver/releases/download/v0.18.0/geckodriver-v0.18.0-linux64.tar.gz
RUN tar -xzvf geckodriver-v0.18.0-linux64.tar.gz
RUN mkdir /app/archives

COPY requirements.txt /app/requirements.txt
RUN pip install --upgrade -r requirements.txt

COPY . /app
RUN python setup.py develop
ENV PATH "$PATH:/app"
CMD hp-creator /app/profile && hp-archiver /app/profile /app/archives
