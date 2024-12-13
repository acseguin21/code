#!/bin/sh

# Check if there are any video files to compress
if ls /videos/*.mp4 1> /dev/null 2>&1; then
    for file in /videos/*.mp4; do
        ffmpeg -i "$file" -vcodec libx265 -crf 28 "compressed_$file"
        mv "compressed_$file" "$file"
    done
else
    echo "No video files to compress."
fi 