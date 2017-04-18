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

COPY ./requirements.txt /
COPY ./app /app
WORKDIR /app
RUN pip install -r /requirements.txt

RUN apk del .build-dependencies

EXPOSE 5000

CMD ["python3", "api.py"]
