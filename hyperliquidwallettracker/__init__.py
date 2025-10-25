"""
HyperLiquidWalletTracker - Advanced Real-Time Hyperliquid Wallet Monitoring System

A modern, production-ready monitoring and alerting system for Hyperliquid
wallet activity with intelligent event processing, multi-channel notifications, and
comprehensive observability features.

Key Features:
- Real-time WebSocket monitoring with automatic reconnection
- Intelligent event deduplication and aggregation
- Multi-channel notification system (Discord, Telegram, Email, Webhooks)
- Advanced position classification (WHALE, LARGE, MEDIUM, NOTABLE)
- Comprehensive monitoring and metrics
- Modern async architecture with proper error handling
"""

__version__ = "1.0.0"
__author__ = "JDENNO91"
__email__ = "jdenno91@example.com"

from .core.monitor import HyperLiquidWalletTracker
from .core.config import HyperLiquidConfig
from .alerts.engine import AlertEngine
from .notifications.dispatcher import NotificationDispatcher

__all__ = [
    "HyperLiquidWalletTracker",
    "HyperLiquidConfig", 
    "AlertEngine",
    "NotificationDispatcher",
]
