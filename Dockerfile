FROM python:3.11-alpine

WORKDIR /hsmqttbridge

RUN adduser -D bridge

COPY --chown=bridge:bridge requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY --chown=bridge:bridge . .

USER bridge

CMD ["python", "main.py"]