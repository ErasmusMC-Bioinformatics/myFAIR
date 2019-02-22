FROM fairdom/seek:1.8

RUN bundle exec rake seek_rdf:generate RAILS_ENV=production
#RUN sed -i 's%"filestore"%"/mnt/filestore/"%' /seek/config/initializers/seek_configuration.rb-openseek
ENV DBA_PASSWORD "dba"
ENV VIRTUOSO "false"