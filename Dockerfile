# Dockerfile for ajax-imou-bridge
# Author: Mykola Marzhan (@delgod)
#
# This Dockerfile uses a multi-stage build to create a lean, secure, and
# efficient container for the SIA Bridge application. It uses standard
# pip and venv to align with the project's structure.

# ==============================================================================
# Builder Stage
#
# This stage installs build-time dependencies and the Python packages into a
# virtual environment. This keeps the final image clean of build tools.
# ==============================================================================
FROM python:3.12-slim-bullseye AS builder

# Set essential environment variables for a clean and predictable build
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on

# Create a virtual environment in a standard location
RUN python -m venv /opt/venv

# Set the PATH to include the virtual environment's binaries
ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /app

# Copy and install dependencies first to leverage Docker layer caching
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy the entire project and install it into the virtual environment.
# This will create the `sia-bridge` executable if defined in pyproject.toml.
COPY . .
RUN pip install .

# ==============================================================================
# Final Stage
#
# This is the lean production image. It copies the virtual environment from the
# builder stage and runs the application as a non-root user for security.
# ==============================================================================
FROM python:3.12-slim-bullseye AS final

# Set runtime environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Create a non-root user and group for security
# The user 'appuser' cannot log in and has no home directory.
RUN groupadd --system appgroup && \
    useradd --system --gid appgroup --shell /sbin/nologin appuser

# Copy the populated virtual environment from the builder stage
COPY --from=builder /opt/venv /opt/venv

# Set the PATH to use the virtual environment's Python and packages
ENV PATH="/opt/venv/bin:$PATH"

# Switch to the non-root user
USER appuser

# Expose the default SIA port for documentation and networking
EXPOSE 12128

# Set up a health check to monitor the TCP listener's status.
# This helps orchestration systems like Docker Swarm or Kubernetes manage the container.
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import socket; s = socket.create_connection(('localhost', 12128), timeout=5)"

# Define the entrypoint for the container.
# This runs the `sia-bridge` command, which was installed in the builder stage.
# Configuration must be supplied via environment variables.
CMD ["sia-bridge"] 