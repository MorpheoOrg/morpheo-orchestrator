FROM python:3-alpine

COPY ./requirements.txt /usr/src/.
RUN apk add --no-cache libstdc++ && \
    apk add --no-cache \
    --repository=http://dl-cdn.alpinelinux.org/alpine/edge/community \
    lapack-dev && \
    apk add --no-cache \
    --virtual=.build-dependencies \
    g++ gfortran musl-dev \
    python3-dev && \
    ln -s locale.h /usr/include/xlocale.h && \
    pip install -r /usr/src/requirements.txt && \
    apk del .build-dependencies

WORKDIR /usr/src/app

COPY ./app /usr/src/app

EXPOSE 5000

CMD ["python3", "api.py"]
