FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN RAG_BACKEND=chroma python -m scripts.build_index

ENV RAG_BACKEND=chroma
ENV MCP_TRANSPORT=stdio
ENV PORT=8000
EXPOSE 8000
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
