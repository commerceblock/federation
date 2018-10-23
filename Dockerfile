FROM python:3.7.0-stretch

COPY . /usr/src

RUN set -x \
    && cd /usr/src \
    && python setup.py build \
    && python setup.py install \
    && pip install -r requirements.txt
    
CMD ["bash","-c"]