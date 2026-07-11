#!/bin/sh
if [ "z$GOOGLE_APPLICATION_CREDENTIALS" = "z" ]; then
    printf "ERROR: GOOGLE_APPLICATION_CREDENTIALS not set.\n"
    exit 1
fi
if [ "z$GAR_IMAGE" = "z" ]; then
   printf "ERROR: GAR_IMAGE not set.\n"
    exit 1
fi

docker run --rm -it \
       -p 8000:8000 \
       --env-file .env \
       -v $(pwd)/data:/app/data \
       -v $GOOGLE_APPLICATION_CREDENTIALS:/app/service-account.json \
       -e GOOGLE_APPLICATION_CREDENTIALS=/app/service-account.json \
       $GAR_IMAGE:dev
