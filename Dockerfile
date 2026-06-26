FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir streamlit pandas beautifulsoup4

COPY app/ ./app/
COPY data/ ./data/

ENV PORT=8080
EXPOSE 8080

CMD exec streamlit run app/app.py \
    --server.port=$PORT \
    --server.address=0.0.0.0 \
    --server.headless=true \
    --browser.gatherUsageStats=false
