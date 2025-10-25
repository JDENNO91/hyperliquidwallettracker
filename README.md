# 🚀 HyperLiquidWalletTracker

**Advanced real-time cryptocurrency wallet monitoring system for Hyperliquid protocol.**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![AsyncIO](https://img.shields.io/badge/async-await-green.svg)](https://docs.python.org/3/library/asyncio.html)

Monitor Hyperliquid wallet addresses in real-time, automatically detecting and alerting on significant trading activity. Classifies positions by size (WHALE, LARGE, MEDIUM, NOTABLE) and sends instant notifications via Discord, Telegram, Email, or Webhooks.

---

## ✨ Key Features

### 🔍 **Real-Time Monitoring**
- **WebSocket Integration**: Direct connection to Hyperliquid's WebSocket API for real-time data
- **Automatic Reconnection**: Robust connection management with exponential backoff
- **Health Monitoring**: Continuous connection validation and automatic recovery
- **Event Processing**: Intelligent event parsing, deduplication, and aggregation

### 🧠 **Intelligent Alert System**
- **Position Classification**: Automatic categorization of trades by USD value:
  - 🐋 **WHALE**: $1M+ positions
  - 🦈 **LARGE**: $100K+ positions  
  - 🐟 **MEDIUM**: $10K+ positions
  - 🦐 **NOTABLE**: $1K+ positions
- **Configurable Thresholds**: Customizable alert levels for different use cases
- **Rule-Based Engine**: Flexible alert rules with time-based conditions
- **Event Deduplication**: Smart filtering to prevent notification spam

### 📢 **Multi-Channel Notifications**
- **Discord Integration**: Rich embeds with position details and market context
- **Telegram Support**: Formatted messages with emojis and structured data
- **Email Alerts**: HTML and text notifications with comprehensive details
- **Webhook Support**: Custom integrations for any external system
- **Rate Limiting**: Intelligent throttling to respect API limits

### 📊 **Advanced Analytics & Monitoring**
- **Prometheus Metrics**: Comprehensive system and business metrics
- **Structured Logging**: JSON-formatted logs with correlation IDs
- **Performance Tracking**: Real-time statistics and health monitoring
- **Event History**: Configurable event storage and analysis

---

## 🚀 Quick Start

### Installation

```bash
pip install -r requirements.txt
```

### CLI Usage

```bash
# Generate sample configuration
python -m hyperliquidwallettracker.cli generate-config --format yaml > config.yaml

# Start monitoring with wallets
python -m hyperliquidwallettracker.cli start --wallets 0x1234... --discord-webhook https://...

# Check system status
python -m hyperliquidwallettracker.cli status

# Test notifications
python -m hyperliquidwallettracker.cli test-notification --wallet 0x1234...
```

### Docker Deployment

```bash
# Build and run with Docker Compose
docker-compose up -d

# Or build custom image
docker build -t hyperliquidwallettracker .
```

---

## ⚙️ Configuration

### Quick Configuration

```bash
# Generate sample config
python -m hyperliquidwallettracker.cli generate-config --format yaml > config.yaml

# Edit configuration
nano config.yaml

# Start with config file
python -m hyperliquidwallettracker.cli start --config config.yaml
```

### Environment Variables

```bash
# Core settings
HYPERLIQUIDWALLETTRACKER_DEBUG=false
HYPERLIQUIDWALLETTRACKER_WEBSOCKET_URL=wss://api.hyperliquid.xyz/ws

# Watched wallets
HYPERLIQUIDWALLETTRACKER_WATCHED_WALLETS=0x1234...abcd,0x5678...efgh

# Position thresholds
HYPERLIQUIDWALLETTRACKER_NOTABLE_THRESHOLD=1000
HYPERLIQUIDWALLETTRACKER_MEDIUM_THRESHOLD=10000
HYPERLIQUIDWALLETTRACKER_LARGE_THRESHOLD=100000
HYPERLIQUIDWALLETTRACKER_WHALE_THRESHOLD=1000000

# Discord notifications
HYPERLIQUIDWALLETTRACKER_DISCORD_WEBHOOK_URL=your_webhook_url

# Telegram notifications
HYPERLIQUIDWALLETTRACKER_TELEGRAM_BOT_TOKEN=your_bot_token
HYPERLIQUIDWALLETTRACKER_TELEGRAM_CHAT_ID=your_chat_id

# Email notifications
HYPERLIQUIDWALLETTRACKER_EMAIL_USERNAME=your_email@example.com
HYPERLIQUIDWALLETTRACKER_EMAIL_PASSWORD=your_password
HYPERLIQUIDWALLETTRACKER_EMAIL_TO_ADDRS=recipient@example.com

# Webhook notifications
HYPERLIQUIDWALLETTRACKER_WEBHOOK_URL=your_webhook_url
```

### Configuration File

```yaml
# config.yaml
watched_wallets:
  - "0x1234abcd5678efgh"
  - "0x5678efgh1234abcd"

thresholds:
  notable_threshold: 1000
  medium_threshold: 10000
  large_threshold: 100000
  whale_threshold: 1000000

discord:
  enabled: true
  webhook_url: "your_discord_webhook_here"

telegram:
  enabled: true
  bot_token: "your_bot_token_here"
  chat_id: "your_chat_id_here"

email:
  enabled: true
  smtp_server: "smtp.gmail.com"
  smtp_port: 587
  username: "your_email@example.com"
  password: "your_password_here"
  from_addr: "alerts@example.com"
  to_addrs:
    - "recipient@example.com"

webhook:
  enabled: true
  url: "https://your-webhook-endpoint.com"
  headers:
    Authorization: "Bearer your_token"
```

---

## 📋 Sample Alert Output

### Discord Notifications
```
🐋 WHALE Position Alert

Detected whale position worth $1,250,000.00

💰 Value: $1,250,000.00
🪙 Coin: BTC
📈 Side: BUY
🔗 Wallet: 0x2ea18c...
⏰ Time: 2024-01-15T14:39:29.000Z UTC
```

### Telegram Notifications
```
🐋 *WHALE ALERT*

🐋 *WHALE Position Alert*

Detected whale position worth $1,250,000.00

💰 *Value:* $1,250,000.00
🪙 *Coin:* BTC
📈 *Side:* BUY
🔗 *Wallet:* `0x2ea18c...`
⏰ *Time:* 2024-01-15T14:39:29.000Z UTC
```

### Email Notifications
```
Subject: HyperLiquid Alert: 🐋 WHALE Position Alert

🐋 WHALE Position Alert

Detected whale position worth $1,250,000.00

Position Details:
- Value: $1,250,000.00
- Coin: BTC
- Side: BUY
- Wallet: 0x2ea18c...
- Time: 2024-01-15T14:39:29.000Z UTC
```

---

## 🏗️ Architecture

### Modern Python Stack
- **Async-First Design**: Built on `asyncio` for high-performance concurrent processing
- **Type Safety**: Full Pydantic integration for robust configuration and validation
- **Structured Logging**: Professional logging with `structlog` for observability
- **Metrics Collection**: Prometheus integration for monitoring and alerting

### Production-Ready Features
- **Docker Containerization**: Complete containerization with Docker and Docker Compose
- **CI/CD Pipeline**: GitHub Actions workflow for automated testing and deployment
- **Configuration Management**: Flexible YAML/JSON configuration with environment variable support
- **Health Checks**: Comprehensive system health monitoring and reporting

### Scalable Design
- **Modular Architecture**: Clean separation of concerns for easy maintenance and extension
- **Event-Driven Processing**: Asynchronous event handling for high throughput
- **Rate Limiting**: Multiple strategies (sliding window, token bucket) for optimal performance
- **Resource Management**: Efficient memory and CPU usage with automatic cleanup

---

## 🎯 Use Cases

### For Traders
- **Whale Tracking**: Monitor large position movements for market insights
- **Competitor Analysis**: Track specific wallet addresses for trading strategies
- **Market Intelligence**: Stay informed about significant trading activity
- **Risk Management**: Get alerts about unusual market movements

### For Analysts
- **Market Research**: Collect data on trading patterns and behaviors
- **Trend Analysis**: Identify emerging trends through position monitoring
- **Portfolio Tracking**: Monitor multiple wallets simultaneously
- **Data Collection**: Export structured data for further analysis

### For Developers
- **API Integration**: Webhook support for custom applications
- **Data Pipeline**: Structured event data for downstream processing
- **Monitoring**: System health and performance metrics
- **Extensibility**: Modular design for custom feature development

---

## 📊 Performance Characteristics

### High Performance
- **Low Latency**: Direct WebSocket connections for real-time data
- **High Throughput**: Async processing handles thousands of events per second
- **Efficient Resource Usage**: Optimized memory and CPU utilization
- **Scalable Architecture**: Designed to handle increasing load gracefully

### Reliability Features
- **Automatic Recovery**: Self-healing connection management
- **Error Handling**: Comprehensive exception handling and logging
- **Data Integrity**: Event deduplication and validation
- **Monitoring**: Real-time health checks and alerting

---

## 🚀 Deployment

### Docker Deployment

```bash
# Build and run with Docker Compose
docker-compose up -d

# Or build custom image
docker build -t hyperliquidwallettracker .
```

### Docker Compose

```yaml
version: '3.8'
services:
  hyperliquidwallettracker:
    build: .
    environment:
      - HYPERLIQUIDWALLETTRACKER_WATCHED_WALLETS=0x1234...abcd
      - HYPERLIQUIDWALLETTRACKER_DISCORD_WEBHOOK_URL=${DISCORD_WEBHOOK}
    volumes:
      - ./config:/app/config
    restart: unless-stopped
```

---

## 🏆 Why Choose HyperLiquidWalletTracker

### ✅ Production Ready
- Battle-tested architecture with comprehensive error handling
- Full monitoring and observability integration
- Docker containerization for easy deployment
- CI/CD pipeline for automated testing and deployment

### ✅ Modern Technology
- Built with modern Python async programming
- Type-safe configuration with Pydantic
- Structured logging and comprehensive metrics
- Clean, maintainable, and well-documented codebase

### ✅ Easy to Use
- Simple CLI interface with intuitive commands
- Flexible configuration options
- Comprehensive documentation and examples
- Quick setup and deployment

---

## 📄 License

Distributed under the MIT License. See [LICENSE](LICENSE) for more information.

---

**HyperLiquidWalletTracker** - *Advanced real-time cryptocurrency monitoring system* 🚀