FROM jrottenberg/ffmpeg:4.3-alpine

RUN mkdir -p /videos
WORKDIR /videos

COPY compress_videos.sh /usr/local/bin/compress_videos.sh
RUN chmod +x /usr/local/bin/compress_videos.sh

ENTRYPOINT ["sh", "-c"]
CMD ["while true; do /usr/local/bin/compress_videos.sh; sleep 3600; done"] 