ARG BASE_IMAGE=toolathlon:base
FROM ${BASE_IMAGE}

ENV SKIP_EXISTING_ARTIFACTS=1
WORKDIR /workspace

# Copy only required runtime/build inputs to keep cache stable and context small.
COPY scripts/ /workspace/scripts/
COPY configs/ /workspace/configs/
COPY local_servers/ /opt/local_servers/
ENV LOCAL_SERVERS_PATH="/opt/local_servers"
WORKDIR /workspace
RUN bash scripts/build_required_mcp_artifacts.sh && \
    find /opt/local_servers -type d -name node_modules -prune -exec rm -rf '{}' +
RUN python scripts/preflight_mcp_paths.py

CMD ["/bin/bash"]
