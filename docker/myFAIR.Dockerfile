FROM continuumio/miniconda3:latest

RUN mkdir /code
WORKDIR /code
ADD requirements.txt requirements.txt

RUN pip install -r requirements.txt
RUN conda install -c conda-forge lftp libmagic sparqlwrapper

COPY . /code

RUN mv myFAIR/docker_settings.py myFAIR/settings.py
RUN chmod 777 /code/docker/myfair_start.sh

EXPOSE :8000

CMD ["/code/docker/myfair_start.sh"]