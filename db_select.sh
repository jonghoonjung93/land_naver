#!/bin/bash

# SQLite 데이터베이스 파일 경로
db_file="land_naver.sqlite3"

# SQLite 쿼리문
query1="SELECT * FROM land_item;"

# SQLite 쿼리 실행
echo "= $query1 ======================================================"
sqlite3 "$db_file" "$query1"
