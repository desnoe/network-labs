#!/usr/bin/env sh

SQL_CLEAR=$(dirname "$0")/clear.sql
SQL_DUMP=$1
PG_URL=$2
PSQL=$(which psql)

"$PSQL" -1 -f "$SQL_CLEAR" "$PG_URL"
"$PSQL" -1 -f "$SQL_DUMP" "$PG_URL"
