#!/bin/bash

START=128
END=512
STEP=8

for (( S_HASH=$START; S_HASH<=$END; S_HASH+=$STEP ))
do
    echo "▶️ Running S_HASH=$S_HASH"
    ./run.sh phash image M_WORKERS=10 C_CHUNK=1 S_HASH=$S_HASH
    echo "✅ Finished S_HASH=$S_HASH"
    echo "-------------------------------"
done
