FROM python:3-alpine

COPY ./requirements.txt /app/requirements.txt
COPY ./vcap-local.json /app/vcap-local.json
WORKDIR /app

RUN apk --update add python3 py-pip openssl ca-certificates py-openssl wget bash linux-headers
RUN apk --update add --virtual build-dependencies libffi-dev openssl-dev python3-dev py-pip build-base \
  && pip install --upgrade pip \
  && pip install --upgrade pipenv\
  && pip install --upgrade -r /app/requirements.txt\
  && apk del build-dependencies

COPY . /app

ENTRYPOINT [ "python3" ]

CMD [ "pythonmongocf.py" ]