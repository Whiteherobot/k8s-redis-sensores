FROM python:3.12-alpine
RUN pip install --no-cache-dir "flask>=3,<4" "redis>=5,<7" "gunicorn>=22,<24"
WORKDIR /app
COPY app.py .
COPY templates ./templates
USER nobody
EXPOSE 8080
CMD ["gunicorn", "-b", "0.0.0.0:8080", "-w", "2", "app:crear_app()"]
