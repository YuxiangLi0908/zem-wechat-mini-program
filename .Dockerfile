# Use official Python image
FROM python:3.10

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    POETRY_VERSION=2.2.0

# Install Poetry
RUN pip install "poetry==$POETRY_VERSION"

# Set work directory
WORKDIR /app

# Copy the project files
COPY pyproject.toml poetry.lock ./

# Install dependencies
RUN poetry install --no-root

# Copy the app folder
COPY app ./app

# Expose port
EXPOSE 8000

# Command to run the FastAPI app
CMD ["poetry", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]