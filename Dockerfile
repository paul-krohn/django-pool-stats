FROM ubuntu:focal

RUN apt-get update -qq
RUN DEBIAN_FRONTEND="noninteractive" TZ="Etc/UTC" apt-get install -y pkg-config libcairo2-dev python3 python3-pip xvfb python3-dev libssl-dev libmysqlclient-dev curl firefox libgirepository1.0-dev mysql-client firefox-geckodriver

ENV PYTHONUNBUFFERED 1
RUN mkdir /code
WORKDIR /code
COPY dev-requirements.txt /code/
COPY requirements.txt /code/
RUN pip3 install --upgrade pip setuptools pycairo
RUN pip3 install -r dev-requirements.txt
COPY . /code/
