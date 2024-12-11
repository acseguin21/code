# Use the official Python image.
FROM python:3.9-slim

# Set environment variables using key=value format
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set work directory
WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project
COPY src/ .

# Expose port
EXPOSE 8080

# Run the application
CMD ["python", "app.py"]