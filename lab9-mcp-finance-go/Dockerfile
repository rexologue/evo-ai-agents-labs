# Multi-stage build для минимального размера образа

# Этап сборки
FROM golang:1.21-alpine AS builder

WORKDIR /build

# Копируем go.mod и go.sum (если есть)
COPY go.mod ./
COPY go.sum* ./
RUN go mod download

# Копируем исходный код
COPY . .

# Собираем приложение
RUN CGO_ENABLED=0 GOOS=linux go build -a -installsuffix cgo -o server ./cmd/server

# Финальный образ
FROM alpine:latest

RUN apk --no-cache add ca-certificates

WORKDIR /app

# Копируем бинарник из builder
COPY --from=builder /build/server .

# Создаем непривилегированного пользователя
RUN addgroup -g 1000 mcp && \
    adduser -D -u 1000 -G mcp mcp && \
    chown -R mcp:mcp /app

USER mcp

# Открываем порт
EXPOSE 8000

# Команда запуска
CMD ["./server"]
