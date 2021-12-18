#!/usr/bin/env sh

SQL_DUMP=$1
PG_URL=$2
PG_DUMP=$(which pg_dump)

$PG_DUMP -v -f "$SQL_DUMP" "$PG_URL"
