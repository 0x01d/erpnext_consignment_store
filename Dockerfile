# Dockerfile for ERPNext with Consignment Store App
FROM frappe/bench:latest

USER root

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    build-essential \
    python3-dev \
    libmariadb-dev \
    && rm -rf /var/lib/apt/lists/*

USER frappe

# Set working directory
WORKDIR /home/frappe/frappe-bench

# Build arguments for versions
ARG FRAPPE_BRANCH=version-15
ARG ERPNEXT_BRANCH=version-15

# Initialize bench if not exists
RUN if [ ! -d "apps/frappe" ]; then \
        bench init --skip-redis-config-generation --frappe-branch=${FRAPPE_BRANCH} .; \
    fi

# Get ERPNext
RUN if [ ! -d "apps/erpnext" ]; then \
        bench get-app --branch=${ERPNEXT_BRANCH} erpnext; \
    fi

# Copy consignment_store app
COPY --chown=frappe:frappe . /home/frappe/frappe-bench/apps/consignment_store

# Install dependencies for consignment_store
RUN cd /home/frappe/frappe-bench/apps/consignment_store && \
    pip3 install --no-cache-dir -e .

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    BENCH_DEVELOPER_MODE=1

# Expose port for development server
EXPOSE 8000 9000

# Default command
CMD ["bench", "start"]
