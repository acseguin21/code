FROM alpine:3.14

RUN apk add --no-cache ffmpeg

RUN mkdir -p /videos
WORKDIR /videos

COPY compress_videos.sh /usr/local/bin/compress_videos.sh
RUN chmod +x /usr/local/bin/compress_videos.sh

CMD ["sh", "-c", "while true; do compress_videos.sh; sleep 3600; done"] 