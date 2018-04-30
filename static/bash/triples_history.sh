#!/usr/bin/env bash
while getopts t:u:r:i:s:d:e:w:m:p:a:b:h: option
do
 case "${option}"
 in
 t) TRIPLEMODE=${OPTARG};;
 u) USERNAME=${OPTARG};;
 r) RESULTID=${OPTARG};;
 i) INVESTIGATION=${OPTARG};;
 s) STUDY=${OPTARG};;
 d) DATE=${OPTARG};;
 e) WORKFLOWID=${OPTARG};;
 w) WORKFLOW=${OPTARG};;
 m) META=${OPTARG};;
 p) PID=${OPTARG};;
 a) HEADER=${OPTARG};;
 b) VALUE=${OPTARG};;
 h) echo -n "Adds new triples to the triple store based on the supplied data "
    echo -n "from the metadata file."
    echo
    exit 1;;
 :) echo "missing argument for -%s\n" "$OPTARG" >&2
       exit 1
       ;;
 esac
done
case "$TRIPLEMODE"
in
1) curl http://127.0.0.1:3030/ds/update -X POST --data 'update=INSERT DATA {
GRAPH <http://127.0.0.1:3030/ds/data/'"$USERNAME"'>{
<http://127.0.0.1:3030/'"$RESULTID"'>
<http://127.0.0.1:3030/ds/data?graph='"$USERNAME"'#pid> '"'$PID'"' }
}' -H 'Accept: text/plain,*/*;q=0.9'
curl http://127.0.0.1:3030/ds/update -X POST --data 'update=INSERT DATA {
GRAPH <http://127.0.0.1:3030/ds/data/'"$USERNAME"'>{
<http://127.0.0.1:3030/'"$RESULTID"'>
<http://127.0.0.1:3030/ds/data?graph='"$USERNAME"'#results_id> 
'"'$RESULTID'"' }}' -H 'Accept: text/plain,*/*;q=0.9'
curl http://127.0.0.1:3030/ds/update -X POST --data 'update=INSERT DATA {
GRAPH <http://127.0.0.1:3030/ds/data/'"$USERNAME"'>{
<http://127.0.0.1:3030/'"$RESULTID"'>
<http://127.0.0.1:3030/ds/data?graph='"$USERNAME"'#group_id> '"'$STUDY'"' }
}' -H 'Accept: text/plain,*/*;q=0.9'
curl http://127.0.0.1:3030/ds/update -X POST --data 'update=INSERT DATA {
GRAPH <http://127.0.0.1:3030/ds/data/'"$USERNAME"'>{
<http://127.0.0.1:3030/'"$RESULTID"'>
<http://127.0.0.1:3030/ds/data?graph='"$USERNAME"'#investigation_id> 
'"'$INVESTIGATION'"' }}' -H 'Accept: text/plain,*/*;q=0.9'
curl http://127.0.0.1:3030/ds/update -X POST --data 'update=INSERT DATA {
GRAPH <http://127.0.0.1:3030/ds/data/'"$USERNAME"'>{
<http://127.0.0.1:3030/'"$RESULTID"'>
<http://127.0.0.1:3030/ds/data?graph='"$USERNAME"'#workflow> '"'$WORKFLOW'"' }
}' -H 'Accept: text/plain,*/*;q=0.9'
curl http://127.0.0.1:3030/ds/update -X POST --data 'update=INSERT DATA {
GRAPH <http://127.0.0.1:3030/ds/data/'"$USERNAME"'>{
<http://127.0.0.1:3030/'"$RESULTID"'>
<http://127.0.0.1:3030/ds/data?graph='"$USERNAME"'#workflowid> 
'"'$WORKFLOWID'"' }}' -H 'Accept: text/plain,*/*;q=0.9'
curl http://127.0.0.1:3030/ds/update -X POST --data 'update=INSERT DATA {
GRAPH <http://127.0.0.1:3030/ds/data/'"$USERNAME"'>{
<http://127.0.0.1:3030/'"$RESULTID"'>
<http://127.0.0.1:3030/ds/data?graph='"$USERNAME"'#date> '"'$DATE'"' }
}' -H 'Accept: text/plain,*/*;q=0.9';;
esac