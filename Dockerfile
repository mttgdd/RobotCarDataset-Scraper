# os
FROM ubuntu:16.04

# apt
RUN apt-get -y update \
	&& apt-get install -y software-properties-common \
	&& apt-get -y update \
	&& apt-get install -y git python-pip python3-pip

# pip
RUN git clone https://github.com/matthewgadd/RobotCarDataset-Scraper.git \
    && cd RobotCarDataset-Scraper \
    && pip3 install -r requirements.txt

# alias
RUN echo 'alias python=python3' >> /root/.bashrc \
	&& echo 'alias pip=pip3' >> /root/.bashrc

# entry point at a working dir
ENTRYPOINT ["/bin/bash"]