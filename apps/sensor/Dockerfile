FROM python:3.12-alpine
RUN pip install --no-cache-dir "redis>=5,<7"
WORKDIR /app
COPY sensor.py .
USER nobody
CMD ["python", "-u", "sensor.py"]
