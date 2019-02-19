FROM fairdom/seek:1.8

RUN bundle exec rake seek_rdf:generate RAILS_ENV=production