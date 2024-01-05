FROM ubuntu:xenial
SHELL ["/bin/bash", "-c"]

# dependencies
RUN apt-get update
RUN apt-get install -y build-essential
RUN apt-get install -y \
    automake pkg-config libtool
RUN apt-get install -y \
    python3-dev python3-pip python3-pyqt4 python3-sip python3-venv

# curl is a better tool
RUN apt-get install -y curl

RUN useradd --home-dir /home/chaum --create-home --shell /bin/bash --skel /etc/skel/ chaum
ARG core_version
ARG core_dist
ARG repo_name
RUN mkdir -p /home/chaum/${repo_name}
COPY ${repo_name} /home/chaum/${repo_name}
RUN ls -la /home/chaum
RUN chown -R chaum:chaum /home/chaum/${repo_name}
USER chaum

# copy node software from the host and install
WORKDIR /home/chaum
RUN ls -la .
RUN ls -la ${repo_name}
RUN ls -la ${repo_name}/deps/cache
RUN tar xaf ./${repo_name}/deps/cache/${core_dist} -C /home/chaum
ENV PATH "/home/chaum/bitcoin-${core_version}/bin:${PATH}"
RUN bitcoind --version | head -1

# install script
WORKDIR ${repo_name}
RUN ./install.sh --with-qt
RUN source jmvenv/bin/activate && ./test/run_tests.sh
