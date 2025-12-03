package config

import (
	"os"
	"strconv"

	"github.com/joho/godotenv"
)

// Config содержит конфигурацию сервера
type Config struct {
	Port            int
	MaxPrincipal    float64
	MaxContribution float64
	MaxMonths       int
	MaxRate         float64
	MaxBalanceCap   float64
	OTELEndpoint    string
	OTELServiceName string
	LogLevel        string
}

// LoadConfig загружает конфигурацию из переменных окружения
func LoadConfig() (*Config, error) {
	// Загружаем .env файл, если он существует (игнорируем ошибку)
	_ = godotenv.Load()

	cfg := &Config{
		Port:            getEnvInt("PORT", 8000),
		MaxPrincipal:    getEnvFloat("MAX_PRINCIPAL", 1e9),
		MaxContribution: getEnvFloat("MAX_CONTRIBUTION", 1e8),
		MaxMonths:       getEnvInt("MAX_MONTHS", 600),
		MaxRate:         getEnvFloat("MAX_RATE", 200),
		MaxBalanceCap:   getEnvFloat("MAX_BALANCE_CAP", 1e12),
		OTELEndpoint:    getEnvString("OTEL_ENDPOINT", ""),
		OTELServiceName: getEnvString("OTEL_SERVICE_NAME", "mcp-finance-server"),
		LogLevel:        getEnvString("LOG_LEVEL", "INFO"),
	}

	return cfg, nil
}

func getEnvString(key, defaultValue string) string {
	if value := os.Getenv(key); value != "" {
		return value
	}
	return defaultValue
}

func getEnvInt(key string, defaultValue int) int {
	if value := os.Getenv(key); value != "" {
		if intValue, err := strconv.Atoi(value); err == nil {
			return intValue
		}
	}
	return defaultValue
}

func getEnvFloat(key string, defaultValue float64) float64 {
	if value := os.Getenv(key); value != "" {
		if floatValue, err := strconv.ParseFloat(value, 64); err == nil {
			return floatValue
		}
	}
	return defaultValue
}

// BalanceCap возвращает максимальный баланс для защиты от переполнения
func (c *Config) BalanceCap() float64 {
	return c.MaxBalanceCap
}
