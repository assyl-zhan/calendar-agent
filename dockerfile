FROM python:3.11-slim

WORKDIR /calen_bot

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "tel.py"]