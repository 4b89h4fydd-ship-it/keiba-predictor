FROM python:3.12-slim
WORKDIR /app
COPY app.py /app/app.py
RUN pip install --no-cache-dir fastapi==0.115.6 uvicorn[standard]==0.34.0 beautifulsoup4==4.12.3
ENV PYTHONUNBUFFERED=1
CMD ["sh","-c","uvicorn app:app --host 0.0.0.0 --port ${PORT:-10000}"]
