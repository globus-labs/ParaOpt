FROM ubuntu:18.10

LABEL maintainer="Ted Summer <ted.summer2@gmail.com>"

SHELL ["/bin/bash", "-c"]

RUN apt-get update
RUN apt-get install -y gcc git-core curl

# get miniconda
RUN curl https://repo.continuum.io/miniconda/Miniconda3-latest-Linux-x86_64.sh -o ~/miniconda.sh
RUN bash ~/miniconda.sh -b -p /root/miniconda
RUN rm ~/miniconda.sh
ENV PATH="/root/miniconda/bin:$PATH"

# create env and install requirements
RUN conda create --name paroptservice_py367 python=3.6.7 --yes
COPY ./requirements.txt ./app/
WORKDIR ./app
RUN source activate paroptservice_py367 && pip install --no-cache-dir -r requirements.txt

COPY ./ ./app
WORKDIR ./app

# expose server
EXPOSE 8080
# expose parsl's HighThroughputExecutor ports
EXPOSE 54000-54100

CMD source activate paroptservice_py367 && python paropt_service/app.py
