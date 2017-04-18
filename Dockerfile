FROM python:3-alpine

RUN apk add --no-cache libstdc++ && \
    apk add --no-cache \
    --repository=http://dl-cdn.alpinelinux.org/alpine/edge/community \
    lapack-dev && \
    apk add --no-cache \
    --virtual=.build-dependencies \
    g++ gfortran musl-dev \
    python3-dev && \
    ln -s locale.h /usr/include/xlocale.h

COPY ./requirements.txt /usr/src/.
COPY ./app /usr/src/app
WORKDIR /usr/src/app
RUN pip install -r /usr/src/requirements.txt

RUN apk del .build-dependencies

EXPOSE 5000

CMD ["python3", "api.py"]
