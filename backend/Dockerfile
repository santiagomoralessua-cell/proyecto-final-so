FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py .
EXPOSE 5000
# 1 proceso con 8 hilos: las métricas de Prometheus viven en la memoria
# del proceso, así que con un solo worker el contador no se reparte
CMD ["gunicorn", "-w", "1", "--threads", "8", "-b", "0.0.0.0:5000", "app:app"]
