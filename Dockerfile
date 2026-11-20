FROM python:3.11-slim

RUN apt-get update \
 && apt-get install -y --no-install-recommends default-jdk-headless \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . .
RUN pip install --no-cache-dir flask gunicorn
EXPOSE 8080

# ✅ Important — this lets Render auto-fill the correct port
# Run as an unprivileged user so student code can't modify the app or system files
RUN useradd --create-home --uid 10001 runner
USER runner

CMD gunicorn -w 2 -b 0.0.0.0:$PORT server:app
