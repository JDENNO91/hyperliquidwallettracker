"""
Modern configuration management for HyperLiquidWalletTracker.

This module provides type-safe configuration management using Pydantic
with environment variable support, validation, and hot-reloading capabilities.
"""

import os
from pathlib import Path
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, validator
from pydantic_settings import BaseSettings


class NotificationChannelConfig(BaseModel):
    """Configuration for a notification channel."""
    enabled: bool = True
    rate_limit_seconds: int = 30


class DiscordConfig(NotificationChannelConfig):
    """Discord notification configuration."""
    webhook_url: Optional[str] = None
    username: str = "CryptoPulse"
    avatar_url: Optional[str] = None


class TelegramConfig(NotificationChannelConfig):
    """Telegram notification configuration."""
    bot_token: Optional[str] = None
    chat_id: Optional[str] = None
    parse_mode: str = "Markdown"


class EmailConfig(NotificationChannelConfig):
    """Email notification configuration."""
    smtp_server: str = "smtp.gmail.com"
    smtp_port: int = 587
    username: Optional[str] = None
    password: Optional[str] = None
    from_addr: Optional[str] = None
    to_addrs: List[str] = []
    use_tls: bool = True


class WebhookConfig(NotificationChannelConfig):
    """Webhook notification configuration."""
    url: Optional[str] = None
    headers: Dict[str, str] = {}
    timeout: int = 30


class PositionThresholds(BaseModel):
    """Position size thresholds for classification."""
    notable_threshold: float = Field(default=1000, description="NOTABLE threshold in USD")
    medium_threshold: float = Field(default=10000, description="MEDIUM threshold in USD")
    large_threshold: float = Field(default=100000, description="LARGE threshold in USD")
    whale_threshold: float = Field(default=1000000, description="WHALE threshold in USD")


class MonitoringConfig(BaseModel):
    """Monitoring and observability configuration."""
    enable_metrics: bool = True
    metrics_port: int = 9090
    health_check_interval: int = 30
    log_level: str = "INFO"
    enable_redis: bool = False
    redis_url: str = "redis://localhost:6379"


class HyperLiquidConfig(BaseSettings):
    """Main configuration class for HyperLiquidWalletTracker."""
    
    # Core settings
    project_name: str = "HyperLiquidWalletTracker"
    version: str = "2.0.0"
    debug: bool = False
    
    # WebSocket settings
    websocket_url: str = "wss://api.hyperliquid.xyz/ws"
    websocket_timeout: int = 30
    reconnect_interval: int = 5
    max_reconnect_attempts: int = 10
    
    # Watched wallets
    watched_wallets: List[str] = Field(default_factory=list)
    
    # Position thresholds
    thresholds: PositionThresholds = Field(default_factory=PositionThresholds)
    
    # Notification channels
    discord: DiscordConfig = Field(default_factory=DiscordConfig)
    telegram: TelegramConfig = Field(default_factory=TelegramConfig)
    email: EmailConfig = Field(default_factory=EmailConfig)
    webhook: WebhookConfig = Field(default_factory=WebhookConfig)
    
    # Monitoring
    monitoring: MonitoringConfig = Field(default_factory=MonitoringConfig)
    
    # File paths
    config_file: Optional[Path] = None
    coin_mappings_file: Path = Field(default=Path("coin_mappings.json"))
    cache_file: Path = Field(default=Path("rate_limiter_cache.json"))
    
    class Config:
        env_prefix = "HYPERLIQUIDWALLETTRACKER_"
        env_file = ".env"
        case_sensitive = False
        
    @validator('watched_wallets', pre=True)
    def parse_wallets(cls, v):
        """Parse wallets from environment variable or config."""
        if isinstance(v, str):
            return [wallet.strip() for wallet in v.split(',') if wallet.strip()]
        return v
    
    @validator('debug')
    def validate_debug(cls, v):
        """Validate debug setting."""
        return bool(v)
    
    def get_enabled_channels(self) -> List[str]:
        """Get list of enabled notification channels."""
        channels = []
        if self.discord.enabled and self.discord.webhook_url:
            channels.append("discord")
        if self.telegram.enabled and self.telegram.bot_token and self.telegram.chat_id:
            channels.append("telegram")
        if self.email.enabled and self.email.username and self.email.to_addrs:
            channels.append("email")
        if self.webhook.enabled and self.webhook.url:
            channels.append("webhook")
        return channels
    
    def validate_configuration(self) -> List[str]:
        """Validate configuration and return any issues."""
        issues = []
        
        if not self.watched_wallets:
            issues.append("No wallets configured for monitoring")
        
        enabled_channels = self.get_enabled_channels()
        if not enabled_channels:
            issues.append("No notification channels configured")
        
        return issues


def load_config(config_path: Optional[Path] = None) -> HyperLiquidConfig:
    """
    Load configuration from file and environment variables.
    
    Args:
        config_path: Optional path to configuration file
        
    Returns:
        Loaded HyperLiquidConfig instance
    """
    if config_path and config_path.exists():
        # Load from specific file
        return HyperLiquidConfig(_env_file=config_path)
    else:
        # Load from default locations
        return HyperLiquidConfig()


# Global configuration instance
config = load_config()
