FROM python:3.12-slim
WORKDIR /opt/audio-aesthetics
COPY engine/requirements.txt engine/requirements.txt
RUN pip install --no-cache-dir -r engine/requirements.txt
COPY engine engine
COPY website website
WORKDIR /opt/audio-aesthetics/engine
EXPOSE 8788
# Localhost-only default. Configure private deployment with HTTPS reverse proxy.
CMD ["python","run.py"]
