FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y \
    build-essential \
    cmake \
    git \
    ninja-build \
    python3 \
    python3-venv \
    python3-pip \
    unzip \
    zip \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /pap
COPY scripts/pap_build_in_container.py /usr/local/bin/pap_build_in_container.py
RUN chmod +x /usr/local/bin/pap_build_in_container.py

CMD ["python3", "/usr/local/bin/pap_build_in_container.py", "--help"]
