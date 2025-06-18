FROM python:3.11-slim
WORKDIR /app
COPY ./api ./api
RUN pip install -r api/requirements.txt
RUN pip install pytest pytest-mock
EXPOSE 5000
CMD ["python", "-m", "api.app"]
