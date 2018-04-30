#!/usr/bin/env bash
while getopts t:u:r:i:s:d:e:v:m:p:a:b:h: option
do
 case "${option}"
 in
 t) TRIPLEMODE=${OPTARG};;
 u) USERNAME=${OPTARG};;
 r) RESULTID=${OPTARG};;
 i) INVESTIGATION=${OPTARG};;
 s) STUDY=${OPTARG};;
 d) DISGENET=${OPTARG};;
 e) EDAM=${OPTARG};;
 v) DISEASE=${OPTARG};;
 m) META=${OPTARG};;
 p) PID=${OPTARG};;
 a) HEADER=${OPTARG};;
 b) VALUE=${OPTARG};;
 h) echo "Adds new triples to the triple store based on the supplied data "
    echo "from the metadata file."
    echo
    exit 1;;
 :) echo "missing argument for -%s\n" "$OPTARG" >&2
       exit 1
       ;;
 esac
done
case "$TRIPLEMODE"
in
0) curl http://127.0.0.1:3030/ds/update -X POST --data 'update=INSERT DATA {
GRAPH <http://127.0.0.1:3030/ds/data/'"$USERNAME"'>{
<http://127.0.0.1:3030/'"$STUDY"'_'"$RESULTID"'>
<http://127.0.0.1:3030/ds/data?graph='"$USERNAME"'#pid> '"'$PID'"' }
}' -H 'Accept: text/plain,*/*;q=0.9';;
1) curl http://127.0.0.1:3030/ds/update -X POST --data 'update=INSERT DATA {
GRAPH <http://127.0.0.1:3030/ds/data/'"$USERNAME"'>{
<http://127.0.0.1:3030/'"$STUDY"'_'"$RESULTID"'>
<http://127.0.0.1:3030/ds/data?graph='"$USERNAME"'#meta> '"'$META'"' }
}' -H 'Accept: text/plain,*/*;q=0.9';;
2) curl http://127.0.0.1:3030/ds/update -X POST --data 'update=INSERT DATA {
GRAPH <http://127.0.0.1:3030/ds/data/'"$USERNAME"'>{
<http://127.0.0.1:3030/'"$STUDY"'_'"$RESULTID"'>
<http://127.0.0.1:3030/ds/data?graph='"$USERNAME"'#investigation_id> 
'"'$INVESTIGATION'"' }}' -H 'Accept: text/plain,*/*;q=0.9'
curl http://127.0.0.1:3030/ds/update -X POST --data 'update=INSERT DATA {
GRAPH <http://127.0.0.1:3030/ds/data/'"$USERNAME"'>{
<http://127.0.0.1:3030/'"$STUDY"'_'"$RESULTID"'>
<http://127.0.0.1:3030/ds/data?graph='"$USERNAME"'#group_id> '"'$STUDY'"' }
}' -H 'Accept: text/plain,*/*;q=0.9'
curl http://127.0.0.1:3030/ds/update -X POST --data 'update=INSERT DATA {
GRAPH <http://127.0.0.1:3030/ds/data/'"$USERNAME"'>{
<http://127.0.0.1:3030/'"$STUDY"'_'"$RESULTID"'>
<http://127.0.0.1:3030/ds/data?graph='"$USERNAME"'#disgenet_iri> 
'"'$DISGENET'"' }}' -H 'Accept: text/plain,*/*;q=0.9'
curl http://127.0.0.1:3030/ds/update -X POST --data 'update=INSERT DATA {
GRAPH <http://127.0.0.1:3030/ds/data/'"$USERNAME"'>{
<http://127.0.0.1:3030/'"$STUDY"'_'"$RESULTID"'>
<http://127.0.0.1:3030/ds/data?graph='"$USERNAME"'#edam_iri> '"'$EDAM'"' }
}' -H 'Accept: text/plain,*/*;q=0.9'
curl http://127.0.0.1:3030/ds/update -X POST --data 'update=INSERT DATA {
GRAPH <http://127.0.0.1:3030/ds/data/'"$USERNAME"'>{
<http://127.0.0.1:3030/'"$STUDY"'_'"$RESULTID"'>
<http://127.0.0.1:3030/ds/data?graph='"$USERNAME"'#disease> '"'$DISEASE'"' }
}' -H 'Accept: text/plain,*/*;q=0.9';;
3) curl http://127.0.0.1:3030/ds/update -X POST --data 'update=INSERT DATA {
GRAPH <http://127.0.0.1:3030/ds/data/'"$USERNAME"'>{
<http://127.0.0.1:3030/'"$STUDY"'_'"$RESULTID"'>
<http://127.0.0.1:3030/ds/data?graph='"$USERNAME"'#'"$HEADER"'> '"'$VALUE'"' }
}' -H 'Accept: text/plain,*/*;q=0.9';;
4) curl http://127.0.0.1:3030/ds/update -X POST --data 'update=INSERT DATA {
GRAPH <http://127.0.0.1:3030/ds/data/'"$USERNAME"'>{
<http://127.0.0.1:3030/'"$STUDY"'_'"$RESULTID"'>
<http://127.0.0.1:3030/ds/data?graph='"$USERNAME"'#sex> '"'$VALUE'"' }
}' -H 'Accept: text/plain,*/*;q=0.9';;
5) curl http://127.0.0.1:3030/ds/update -X POST --data 'update=WITH 
<http://127.0.0.1:3030/ds/data/'"$USERNAME"'> DELETE {?s ?p ?o} WHERE {
?s <http://127.0.0.1:3030/ds/data?graph='"$USERNAME"'#group_id> ?group . FILTER
(?group = '"'$STUDY'"') ?s ?p ?o }' -H 'Accept: text/plain,*/*;q=0.9';;
6) curl http://127.0.0.1:3030/ds/update -X POST --data 'update=WITH 
<http://127.0.0.1:3030/ds/data/'"$USERNAME"'> DELETE {?s ?p ?o} WHERE {
?s <http://127.0.0.1:3030/ds/data?graph='"$USERNAME"'#investigation_id> 
?group . FILTER(?group = '"'$STUDY'"') 
?s ?p ?o }' -H 'Accept: text/plain,*/*;q=0.9';;
esac