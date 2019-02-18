FROM bgruening/galaxy-stable

MAINTAINER r.jansen.1@erasmusmc.nl, d.vanzessen@erasmusmc.nl

ENV GALAXY_CONFIG_BRAND "myFAIR Galaxy"
ENV GALAXY_CONFIG_CONDA_AUTO_INSTALL "True"
ENV GALAXY_CONFIG_CONDA_AUTO_INIT "True"

WORKDIR /galaxy-central

ADD galaxy_tools.yml $GALAXY_ROOT/tools.yaml

RUN install-tools $GALAXY_ROOT/tools.yaml

VOLUME ["/export/", "/data/", "/var/lib/docker"]

EXPOSE :80
EXPOSE :21
EXPOSE :8080

CMD ["/usr/bin/startup"]