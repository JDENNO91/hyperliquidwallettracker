"""
Command-line interface for HyperLiquidWalletTracker.

This module provides a modern CLI using Click for managing the
HyperLiquidWalletTracker application.
"""

import asyncio
import json
import sys
from pathlib import Path
from typing import List, Optional

import click
from click import echo, secho, style

from .core.config import HyperLiquidConfig
from .core.monitor import HyperLiquidWalletTracker
from .utils.logging import setup_logging, get_logger

logger = get_logger(__name__)


@click.group()
@click.version_option(version="2.0.0", prog_name="HyperLiquidWalletTracker")
@click.option(
    "--config", 
    "-c", 
    type=click.Path(exists=True, path_type=Path),
    help="Path to configuration file"
)
@click.option(
    "--log-level",
    type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]),
    default="INFO",
    help="Logging level"
)
@click.option(
    "--log-format",
    type=click.Choice(["json", "console"]),
    default="console",
    help="Log output format"
)
@click.pass_context
def cli(ctx, config: Optional[Path], log_level: str, log_format: str):
    """
    HyperLiquidWalletTracker - Advanced Hyperliquid wallet monitoring system.
    
    Monitor Hyperliquid wallet activity in real-time with intelligent
    alerting and multi-channel notifications.
    """
    # Setup logging
    setup_logging(level=log_level, format_type=log_format)
    
    # Load configuration
    if config:
        try:
            config_obj = HyperLiquidConfig.load_from_yaml(config)
        except Exception as e:
            secho(f"Error loading configuration: {e}", fg="red")
            sys.exit(1)
    else:
        config_obj = HyperLiquidConfig()
    
    # Store in context
    ctx.obj = {
        "config": config_obj,
        "cli_options": {
            "log_level": log_level,
            "log_format": log_format
        }
    }


@cli.command()
@click.option(
    "--wallets",
    "-w",
    multiple=True,
    help="Wallet addresses to monitor (can be specified multiple times)"
)
@click.option(
    "--discord-webhook",
    help="Discord webhook URL for notifications"
)
@click.option(
    "--telegram-token",
    help="Telegram bot token"
)
@click.option(
    "--telegram-chat",
    help="Telegram chat ID"
)
@click.option(
    "--email-smtp",
    help="SMTP server for email notifications"
)
@click.option(
    "--email-from",
    help="From email address"
)
@click.option(
    "--email-to",
    multiple=True,
    help="To email addresses (can be specified multiple times)"
)
@click.option(
    "--webhook-url",
    help="Webhook URL for notifications"
)
@click.option(
    "--whale-threshold",
    type=float,
    help="Whale position threshold in USD"
)
@click.option(
    "--large-threshold", 
    type=float,
    help="Large position threshold in USD"
)
@click.option(
    "--medium-threshold",
    type=float,
    help="Medium position threshold in USD"
)
@click.option(
    "--notable-threshold",
    type=float,
    help="Notable position threshold in USD"
)
@click.pass_context
def start(
    ctx,
    wallets: List[str],
    discord_webhook: Optional[str],
    telegram_token: Optional[str],
    telegram_chat: Optional[str],
    email_smtp: Optional[str],
    email_from: Optional[str],
    email_to: List[str],
    webhook_url: Optional[str],
    whale_threshold: Optional[float],
    large_threshold: Optional[float],
    medium_threshold: Optional[float],
    notable_threshold: Optional[float]
):
    """Start the HyperLiquidWalletTracker monitor."""
    config = ctx.obj["config"]
    
    # Update configuration with CLI options
    if wallets:
        config.watched_wallets = list(wallets)
    
    if discord_webhook:
        config.discord.enabled = True
        config.discord.webhook_url = discord_webhook
    
    if telegram_token and telegram_chat:
        config.telegram.enabled = True
        config.telegram.bot_token = telegram_token
        config.telegram.chat_id = telegram_chat
    
    if email_smtp and email_from and email_to:
        config.email.enabled = True
        config.email.smtp_server = email_smtp
        config.email.from_addr = email_from
        config.email.to_addrs = list(email_to)
    
    if webhook_url:
        config.webhook.enabled = True
        config.webhook.url = webhook_url
    
    # Update thresholds
    if whale_threshold:
        config.thresholds.whale_threshold = whale_threshold
    if large_threshold:
        config.thresholds.large_threshold = large_threshold
    if medium_threshold:
        config.thresholds.medium_threshold = medium_threshold
    if notable_threshold:
        config.thresholds.notable_threshold = notable_threshold
    
    # Validate configuration
    if not config.watched_wallets:
        secho("Error: No wallets specified for monitoring", fg="red")
        secho("Use --wallets option or configure in config file", fg="yellow")
        sys.exit(1)
    
    # Display configuration
    echo("\n" + "="*60)
    secho("HyperLiquidWalletTracker Configuration", fg="cyan", bold=True)
    echo("="*60)
    echo(f"Wallets to monitor: {len(config.watched_wallets)}")
    for wallet in config.watched_wallets:
        echo(f"  • {wallet[:8]}...")
    
    echo(f"\nPosition thresholds:")
    echo(f"  • Whale: ${config.thresholds.whale_threshold:,.0f}")
    echo(f"  • Large: ${config.thresholds.large_threshold:,.0f}")
    echo(f"  • Medium: ${config.thresholds.medium_threshold:,.0f}")
    echo(f"  • Notable: ${config.thresholds.notable_threshold:,.0f}")
    
    echo(f"\nNotification channels:")
    echo(f"  • Discord: {'✓' if config.discord.enabled else '✗'}")
    echo(f"  • Telegram: {'✓' if config.telegram.enabled else '✗'}")
    echo(f"  • Email: {'✓' if config.email.enabled else '✗'}")
    echo(f"  • Webhook: {'✓' if config.webhook.enabled else '✗'}")
    
    echo("\n" + "="*60)
    secho("Starting monitor...", fg="green", bold=True)
    echo("="*60)
    
    # Start the monitor
    try:
        monitor = HyperLiquidWalletTracker(config)
        asyncio.run(monitor.start())
    except KeyboardInterrupt:
        secho("\nShutdown requested by user", fg="yellow")
    except Exception as e:
        secho(f"\nError starting monitor: {e}", fg="red")
        sys.exit(1)


@cli.command()
@click.option(
    "--output",
    "-o",
    type=click.Path(path_type=Path),
    help="Output file path (default: stdout)"
)
@click.pass_context
def config(ctx, output: Optional[Path]):
    """Display current configuration."""
    config = ctx.obj["config"]
    
    config_dict = {
        "watched_wallets": config.watched_wallets,
        "websocket_url": str(config.websocket_url),
        "thresholds": {
            "whale_threshold": config.thresholds.whale_threshold,
            "large_threshold": config.thresholds.large_threshold,
            "medium_threshold": config.thresholds.medium_threshold,
            "notable_threshold": config.thresholds.notable_threshold,
        },
        "notifications": {
            "discord": {
                "enabled": config.discord.enabled,
                "webhook_url": str(config.discord.webhook_url) if config.discord.webhook_url else None
            },
            "telegram": {
                "enabled": config.telegram.enabled,
                "bot_token": config.telegram.bot_token,
                "chat_id": config.telegram.chat_id
            },
            "email": {
                "enabled": config.email.enabled,
                "smtp_server": config.email.smtp_server,
                "smtp_port": config.email.smtp_port,
                "username": config.email.username,
                "from_addr": str(config.email.from_addr) if config.email.from_addr else None,
                "to_addrs": [str(addr) for addr in config.email.to_addrs]
            },
            "webhook": {
                "enabled": config.webhook.enabled,
                "url": str(config.webhook.url) if config.webhook.url else None,
                "headers": config.webhook.headers
            }
        }
    }
    
    config_json = json.dumps(config_dict, indent=2, default=str)
    
    if output:
        output.write_text(config_json)
        secho(f"Configuration saved to {output}", fg="green")
    else:
        echo(config_json)


@cli.command()
@click.pass_context
def status(ctx):
    """Display system status and health."""
    config = ctx.obj["config"]
    
    echo("\n" + "="*60)
    secho("HyperLiquidWalletTracker Status", fg="cyan", bold=True)
    echo("="*60)
    
    # Configuration status
    echo("Configuration:")
    echo(f"  • Wallets monitored: {len(config.watched_wallets)}")
    echo(f"  • WebSocket URL: {config.websocket_url}")
    
    # Notification channels
    echo("\nNotification Channels:")
    echo(f"  • Discord: {'✓ Enabled' if config.discord.enabled else '✗ Disabled'}")
    echo(f"  • Telegram: {'✓ Enabled' if config.telegram.enabled else '✗ Disabled'}")
    echo(f"  • Email: {'✓ Enabled' if config.email.enabled else '✗ Disabled'}")
    echo(f"  • Webhook: {'✓ Enabled' if config.webhook.enabled else '✗ Disabled'}")
    
    # Thresholds
    echo("\nPosition Thresholds:")
    echo(f"  • Whale: ${config.thresholds.whale_threshold:,.0f}")
    echo(f"  • Large: ${config.thresholds.large_threshold:,.0f}")
    echo(f"  • Medium: ${config.thresholds.medium_threshold:,.0f}")
    echo(f"  • Notable: ${config.thresholds.notable_threshold:,.0f}")
    
    echo("\n" + "="*60)


@cli.command()
@click.option(
    "--wallet",
    "-w",
    required=True,
    help="Wallet address to test"
)
@click.option(
    "--channel",
    "-c",
    type=click.Choice(["discord", "telegram", "email", "webhook"]),
    help="Notification channel to test (default: all enabled)"
)
@click.pass_context
def test_notification(ctx, wallet: str, channel: Optional[str]):
    """Test notification channels with a sample alert."""
    config = ctx.obj["config"]
    
    # Create test notification
    test_notification = {
        "rule_name": "test_notification",
        "rule_severity": "info",
        "context": type('Context', (), {
            'wallet': wallet,
            'event_type': 'test',
            'position_size': None,
            'usd_value': 50000.0,
            'coin': 'BTC',
            'side': 'BUY',
            'timestamp': None,
            'additional_data': {}
        })(),
        "event": {
            "type": "test",
            "wallet": wallet,
            "coin": "BTC",
            "side": "BUY",
            "usd_value": 50000.0
        },
        "formatted": {
            "discord": {
                "username": "HyperLiquid Tracker",
                "embeds": [{
                    "title": "🧪 Test Notification",
                    "description": "This is a test notification from HyperLiquidWalletTracker",
                    "color": 0x00ff00,
                    "fields": [
                        {"name": "💰 Value", "value": "$50,000.00", "inline": True},
                        {"name": "🪙 Coin", "value": "BTC", "inline": True},
                        {"name": "🔗 Wallet", "value": f"`{wallet[:8]}...`", "inline": True}
                    ]
                }]
            },
            "telegram": "🧪 *Test Notification*\n\nThis is a test notification from HyperLiquidWalletTracker\n\n💰 *Value:* $50,000.00\n🪙 *Coin:* BTC\n🔗 *Wallet:* `test_wallet`",
            "email": {
                "subject": "HyperLiquid Alert: 🧪 Test Notification",
                "html_body": "<html><body><h1>🧪 Test Notification</h1><p>This is a test notification from HyperLiquidWalletTracker</p></body></html>",
                "text_body": "🧪 Test Notification\n\nThis is a test notification from HyperLiquidWalletTracker"
            },
            "webhook": {
                "alert_type": "test",
                "title": "🧪 Test Notification",
                "description": "This is a test notification from HyperLiquidWalletTracker"
            }
        }
    }
    
    async def test_channels():
        from .notifications.dispatcher import NotificationDispatcher
        
        dispatcher = NotificationDispatcher(config)
        await dispatcher.start()
        
        try:
            results = await dispatcher.dispatch_notification(test_notification)
            
            echo("\nTest Results:")
            for result in results:
                status = "✓ Success" if result.success else "✗ Failed"
                color = "green" if result.success else "red"
                secho(f"  • {result.channel}: {status}", fg=color)
                if not result.success and result.error_message:
                    echo(f"    Error: {result.error_message}")
        
        finally:
            await dispatcher.stop()
    
    secho("Testing notification channels...", fg="yellow")
    asyncio.run(test_channels())


@cli.command()
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["json", "yaml"]),
    default="yaml",
    help="Output format"
)
@click.option(
    "--output",
    "-o",
    type=click.Path(path_type=Path),
    help="Output file path (default: stdout)"
)
def generate_config(output_format: str, output: Optional[Path]):
    """Generate a sample configuration file."""
    sample_config = {
        "watched_wallets": [
            "0x1234567890abcdef1234567890abcdef12345678",
            "0xabcdef1234567890abcdef1234567890abcdef12"
        ],
        "websocket_url": "wss://api.hyperliquid.xyz/ws",
        "thresholds": {
            "whale_threshold": 1000000.0,
            "large_threshold": 100000.0,
            "medium_threshold": 10000.0,
            "notable_threshold": 1000.0
        },
        "notifications": {
            "discord": {
                "enabled": False,
                "webhook_url": "https://discord.com/api/webhooks/..."
            },
            "telegram": {
                "enabled": False,
                "bot_token": "1234567890:ABCDEFGHIJKLMNOPQRSTUVWXYZ",
                "chat_id": "@your_channel"
            },
            "email": {
                "enabled": False,
                "smtp_server": "smtp.gmail.com",
                "smtp_port": 587,
                "username": "your-email@gmail.com",
                "password": "your-app-password",
                "from_addr": "your-email@gmail.com",
                "to_addrs": ["recipient@example.com"]
            },
            "webhook": {
                "enabled": False,
                "url": "https://your-webhook-url.com/endpoint",
                "headers": {
                    "Authorization": "Bearer your-token"
                }
            }
        }
    }
    
    if output_format == "json":
        content = json.dumps(sample_config, indent=2)
    else:  # yaml
        try:
            import yaml
            content = yaml.dump(sample_config, default_flow_style=False, indent=2)
        except ImportError:
            secho("PyYAML not installed. Install with: pip install pyyaml", fg="red")
            sys.exit(1)
    
    if output:
        output.write_text(content)
        secho(f"Sample configuration saved to {output}", fg="green")
    else:
        echo(content)


if __name__ == "__main__":
    cli()