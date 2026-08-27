FROM python:3.11-slim
WORKDIR /app

RUN useradd -m bridge
USER bridge
COPY --chown=bridge:bridge . /app/

RUN pip install --no-cache-dir -r requirements.txt


CMD ["python", "main.py"]