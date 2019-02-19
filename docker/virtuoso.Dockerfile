FROM tenforce/virtuoso:1.3.1-virtuoso7.2.2

ADD virtuoso_start.sh /virtuoso_start.sh
ADD virtuoso_start_grant.sh /virtuoso_start_grant.sh

RUN chmod 777 /virtuoso_start.sh
RUN chmod 777 /virtuoso_start_grant.sh

ENV SPARQL_UPDATE "true"
ENV DEFAULT_GRAPH "seek:public"

EXPOSE :8890

CMD ["/virtuoso_start.sh"]