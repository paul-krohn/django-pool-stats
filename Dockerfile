FROM ubuntu:bionic

RUN apt-get update -qq
RUN apt-get install -y python3 python3-pip xvfb python3-dev libssl-dev libmysqlclient-dev curl firefox

RUN apt-get install -y mysql-client
RUN curl -L https://github.com/mozilla/geckodriver/releases/download/v0.24.0/geckodriver-v0.24.0-linux64.tar.gz \
  -o /tmp/geckodriver-v0.24.0-linux64.tar.gz
RUN tar -xzf /tmp/geckodriver-v0.24.0-linux64.tar.gz -C /usr/local/bin &&\
    rm /tmp/geckodriver-v0.24.0-linux64.tar.gz
RUN chmod +x /usr/local/bin/geckodriver

ENV PYTHONUNBUFFERED 1
RUN mkdir /code
WORKDIR /code
COPY dev-requirements.txt /code/
COPY requirements.txt /code/
RUN pip3 install -r dev-requirements.txt
COPY . /code/

