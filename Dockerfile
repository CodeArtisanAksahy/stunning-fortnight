FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

COPY app ./app

# OAuth credentials and runtime configuration are supplied by the deployment
# environment; neither should be included in the image.
CMD ["python", "-m", "app.main", "--max-emails", "10"]
