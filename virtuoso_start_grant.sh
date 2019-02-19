#!/bin/bash
sleep 10

echo "Granting rights"
echo 'grant execute on SPARQL_DELETE_DICT_CONTENT to "SPARQL";' | isql-v -U dba
echo 'grant execute on SPARQL_DELETE_DICT_CONTENT to SPARQL_UPDATE;' | isql-v -U dba
echo "Granted rights"