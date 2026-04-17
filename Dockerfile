FROM python:3.12-slim

WORKDIR /app

# instala dependências primeiro (layer cacheável)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# copia o código
COPY app/ ./app/
COPY static/ ./static/

# cria pastas que precisam existir
RUN mkdir -p uploads

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
