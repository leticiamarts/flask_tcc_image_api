FROM python:3.11-slim
WORKDIR /app
COPY ./api ./api
RUN pip install --no-cache-dir -r api/requirements.txt
RUN pip install --no-cache-dir pytest pytest-mock
EXPOSE 5000
CMD ["python", "-m", "api.app"]
