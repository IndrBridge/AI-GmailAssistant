#!/bin/bash

# Check if ImageMagick is installed
if ! command -v convert &> /dev/null; then
    echo "ImageMagick is required but not installed. Please install it first."
    exit 1
fi

# Create icons of different sizes
for size in 16 48 128; do
    convert -size ${size}x${size} xc:white \
        -fill '#1a73e8' \
        -draw "circle $((size/2)),$((size/2)) $((size/2)),0" \
        -draw "path 'M$((size*3/8)),$((size*3/8)) L$((size*5/8)),$((size/2)) L$((size*3/8)),$((size*5/8)) Z'" \
        public/icon${size}.png
done

echo "Icons generated successfully!"
