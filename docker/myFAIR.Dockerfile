FROM continuumio/miniconda3:latest

RUN mkdir /code
COPY . /code
WORKDIR /code

RUN pip install -r requirements.txt
RUN conda install -c conda-forge lftp libmagic sparqlwrapper

RUN mv myFAIR/docker_settings.py myFAIR/settings.py
RUN chmod 777 /code/docker/myfair_start.sh

EXPOSE :8000

CMD ["/code/docker/myfair_start.sh"]