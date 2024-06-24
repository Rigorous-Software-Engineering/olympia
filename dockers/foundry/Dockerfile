FROM debian:bookworm

ENV DEBIAN_FRONTEND="noninteractive"

### root user for system setup
USER root

### debian system setup
RUN apt-get update
RUN apt-get install -y vim git curl sudo \
    bash libssl-dev python3 python3-dev \
    python3-pip time

### install solidity compiler using pip
RUN python3 -m pip install solc-select --break-system-packages

### add maze user and group and make it sudoer
RUN addgroup --gid 1000 maze && \
    adduser --gid 1000 --uid 1000 --shell /bin/bash --home /home/maze maze
RUN echo 'maze  ALL=(root) NOPASSWD: ALL' >> /etc/sudoers

### switch to maze user
USER maze

### setup folder structure
RUN mkdir -p /home/maze && \
    mkdir -p /home/maze/tools && \
    mkdir -p /home/maze/workspace && \
    mkdir -p /home/maze/workspace/build && \
    mkdir -p /home/maze/workspace/outputs && \
    mkdir -p /home/maze/outputs && \
    mkdir -p /home/maze/maze
WORKDIR /home/maze

### setup foundry
### (https://github.com/foundry-rs/foundry/blob/master/foundryup/README.md)
RUN curl -L https://foundry.paradigm.xyz | bash
ENV PATH=/home/maze/.foundry/bin:$PATH
RUN bash -c "foundryup"

### add scripts
ADD --chown=1000:1000 utils.py /home/maze/tools/utils.py
ADD --chown=1000:1000 run_foundry.sh /home/maze/tools/run_foundry.sh
ADD --chown=1000:1000 get_tcs.py /home/maze/tools/get_tcs.py

WORKDIR /home/maze/workspace
