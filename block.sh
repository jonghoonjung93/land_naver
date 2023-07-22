#!/bin/bash

while IFS=',' read -r NUM ADDR MEMO; do
    # Process the variables here
    # echo "Variable 1: $NUM"
    # echo "Variable 2: $ADDR"
    # echo "Variable 3: $MEMO"
    echo '  "BLD'${NUM}'": {'
    echo '    "MEMO": "'${MEMO}'",'
    echo '    "ADDRESS": "고양시 일산동구 '${ADDR}'",'
    echo '    "URL": "",'
    echo '    "NAVER_BLD_ID": ""'
    echo '  },'
done < block.data

