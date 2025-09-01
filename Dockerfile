FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file first
COPY requirements.txt .

# Install pipenv and dependencies from requirements.txt
RUN pip install --no-cache-dir pipenv && \
    pipenv install -r requirements.txt && \
    pipenv requirements > requirements.frozen.txt && \
    pip install -r requirements.frozen.txt && \
    pip uninstall -y pipenv virtualenv-clone virtualenv

# Copy application code
COPY . .

# Expose port for Flask application
EXPOSE 5000

# Command to run the application
CMD ["python", "app.py"]