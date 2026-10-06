FROM debian:13-slim
RUN apt-get update \
    && apt-get install -y --no-install-recommends bash zsh git jq perl ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && ! command -v python \
    && ! command -v python3
WORKDIR /tmp
ENTRYPOINT ["/bin/bash", "/checks/runtime.sh"]
