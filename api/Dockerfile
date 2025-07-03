FROM python:3.11-slim
WORKDIR /app
COPY . . 
RUN pip install -r requirements.txt
RUN pip install pytest pytest-mock
EXPOSE 5000
CMD ["python", "app.py"]
