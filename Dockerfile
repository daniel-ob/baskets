# pull base image
FROM python:3.9-alpine

# set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# set work directory
WORKDIR /code

# install dependencies system-wide (docker container is the virtual environment)
COPY Pipfile Pipfile.lock /code/
RUN pip --disable-pip-version-check install pipenv && pipenv install --system

# Copy project
COPY . /code/