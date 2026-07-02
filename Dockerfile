FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# We removed EXPOSE and uvicorn. This tells Railway to just run the script safely.
CMD ["python", "main.py"]
