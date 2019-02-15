FROM continuumio/miniconda3:latest

RUN mkdir /code
COPY . /code
WORKDIR /code

RUN pip install -r requirements.txt
RUN conda install -c conda-forge lftp libmagic

RUN mv myFAIR/docker_settings.py myFAIR/settings.py
RUN chmod 777 /code/start.sh