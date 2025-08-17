FROM python:3.11-slim
WORKDIR /app
COPY src/ src/
COPY transmission-rss.conf.example ./transmission-rss.conf
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
CMD ["python", "src/transmission_rss.py", "transmission-rss.conf"]
