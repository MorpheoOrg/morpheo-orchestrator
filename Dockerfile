FROM frolvlad/alpine-python3

RUN apk add --no-cache libstdc++ && \
    apk add --no-cache \
    --repository=http://dl-cdn.alpinelinux.org/alpine/edge/community \
    lapack-dev && \
    apk add --no-cache \
    --virtual=.build-dependencies \
    g++ gfortran musl-dev \
    python3-dev && \
    ln -s locale.h /usr/include/xlocale.h

ADD ./requirements.txt .
RUN pip install -r requirements.txt

EXPOSE 5000

ENTRYPOINT ["python3" , "/app/api.py"]
