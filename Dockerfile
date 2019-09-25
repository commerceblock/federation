FROM python:3.7.0-stretch

COPY . /usr/src

RUN set -x \
    && cd /usr/src \
    && apt update \
    && apt install -y netcat \
    && python setup.py build \
    && python setup.py install \
    && pip install -r requirements.txt

COPY docker-entrypoint.sh /docker-entrypoint.sh

ENTRYPOINT ["/docker-entrypoint.sh"]
