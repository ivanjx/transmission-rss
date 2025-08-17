FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y iputils-ping
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY transmission-rss.conf.example ./transmission-rss.conf
COPY src/ src/

CMD ["python", "src/transmission_rss.py", "transmission-rss.conf"]
