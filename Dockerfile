FROM alpine:latest

COPY . /app/
RUN apk --no-cache add python3 openssl && \
        apk --no-cache add --virtual install_deps build-base python3-dev libffi-dev openssl-dev && \
        pip3 install -r /app/requirements.txt && \
        apk del install_deps

WORKDIR /app
CMD ["sh", "-c", "sleep 3 && python3 -u -m twitch-markov"]
