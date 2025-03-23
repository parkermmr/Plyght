FROM python:3.12-slim as builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /install

COPY pyproject.toml poetry.lock* ./

RUN pip install --upgrade pip && pip install poetry

RUN poetry config virtualenvs.create false && poetry install

FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY --from=builder /usr/local /usr/local

COPY . .

ENTRYPOINT ["python", "-m", "app.main"]
