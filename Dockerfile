FROM python:3.11-slim

LABEL maintainer="Apex-Council Contributors"
LABEL description="The Multi-LLM Code Supreme Court: Google Gemini × Anthropic Claude × OpenAI"

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY . /app

RUN pip install --no-cache-dir -e .

EXPOSE 8080

ENV PYTHONUNBUFFERED=1

ENTRYPOINT ["apex-council"]
CMD ["serve", "--host", "0.0.0.0", "--port", "8080"]
