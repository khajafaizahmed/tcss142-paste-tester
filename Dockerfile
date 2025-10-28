FROM python:3.11-slim
RUN apt-get update && apt-get install -y openjdk-17-jdk-headless && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY . .
RUN pip install flask gunicorn
EXPOSE 8080
CMD ["gunicorn", "-w", "2", "-b", "0.0.0.0:8080", "server:app"]
