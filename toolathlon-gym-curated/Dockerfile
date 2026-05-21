ARG BASE_IMAGE=toolathlon:base
FROM ${BASE_IMAGE}

WORKDIR /workspace

# Copy only required runtime/build inputs to keep cache stable and context small.
COPY scripts/ /workspace/scripts/
COPY configs/ /workspace/configs/
COPY local_servers/ /opt/local_servers/
ENV LOCAL_SERVERS_PATH="/opt/local_servers"
WORKDIR /workspace
RUN bash scripts/build_required_mcp_artifacts.sh

CMD ["/bin/bash"]
