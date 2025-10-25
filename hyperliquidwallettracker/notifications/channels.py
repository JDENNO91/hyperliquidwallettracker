"""
Notification channel implementations for HyperLiquidWalletTracker.

This module provides implementations for sending notifications via
Discord, Telegram, Email, and Webhook channels.
"""

import asyncio
import aiohttp
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Any, Optional
from urllib.parse import urlparse

from ..utils.logging import get_logger

logger = get_logger(__name__)


async def send_discord_notification(webhook_url: str, content: Dict[str, Any]) -> bool:
    """
    Send notification to Discord webhook.
    
    Args:
        webhook_url: Discord webhook URL
        content: Discord webhook payload
        
    Returns:
        True if sent successfully, False otherwise
    """
    if not webhook_url:
        logger.warning("Discord webhook URL not configured")
        return False
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(webhook_url, json=content) as response:
                if response.status == 204:
                    logger.info("Discord notification sent successfully")
                    return True
                else:
                    error_text = await response.text()
                    logger.error(f"Discord notification failed: {response.status} - {error_text}")
                    return False
                    
    except Exception as e:
        logger.error(f"Error sending Discord notification: {e}")
        return False


async def send_telegram_notification(
    bot_token: str, 
    chat_id: str, 
    content: str
) -> bool:
    """
    Send notification to Telegram.
    
    Args:
        bot_token: Telegram bot token
        chat_id: Telegram chat ID
        content: Message content
        
    Returns:
        True if sent successfully, False otherwise
    """
    if not bot_token or not chat_id:
        logger.warning("Telegram bot token or chat ID not configured")
        return False
    
    try:
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": content,
            "parse_mode": "Markdown",
            "disable_web_page_preview": True
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as response:
                if response.status == 200:
                    logger.info("Telegram notification sent successfully")
                    return True
                else:
                    error_text = await response.text()
                    logger.error(f"Telegram notification failed: {response.status} - {error_text}")
                    return False
                    
    except Exception as e:
        logger.error(f"Error sending Telegram notification: {e}")
        return False


async def send_email_notification(
    email_config: Any, 
    content: Dict[str, str]
) -> bool:
    """
    Send notification via email.
    
    Args:
        email_config: Email configuration object
        content: Email content (subject, html_body, text_body)
        
    Returns:
        True if sent successfully, False otherwise
    """
    if not email_config.enabled:
        logger.warning("Email notifications not enabled")
        return False
    
    if not email_config.smtp_server or not email_config.username:
        logger.warning("Email SMTP configuration incomplete")
        return False
    
    try:
        # Create message
        msg = MIMEMultipart("alternative")
        msg["From"] = email_config.from_addr
        msg["To"] = ", ".join(str(addr) for addr in email_config.to_addrs)
        msg["Subject"] = content["subject"]
        
        # Add text and HTML parts
        text_part = MIMEText(content["text_body"], "plain")
        html_part = MIMEText(content["html_body"], "html")
        
        msg.attach(text_part)
        msg.attach(html_part)
        
        # Send email
        with smtplib.SMTP(email_config.smtp_server, email_config.smtp_port) as server:
            if email_config.username and email_config.password:
                server.starttls()
                server.login(email_config.username, email_config.password)
            
            server.send_message(msg)
            logger.info("Email notification sent successfully")
            return True
            
    except Exception as e:
        logger.error(f"Error sending email notification: {e}")
        return False


async def send_webhook_notification(
    webhook_url: str, 
    headers: Dict[str, str], 
    content: Dict[str, Any]
) -> bool:
    """
    Send notification to webhook.
    
    Args:
        webhook_url: Webhook URL
        headers: Additional headers
        content: Webhook payload
        
    Returns:
        True if sent successfully, False otherwise
    """
    if not webhook_url:
        logger.warning("Webhook URL not configured")
        return False
    
    try:
        # Prepare headers
        request_headers = {
            "Content-Type": "application/json",
            "User-Agent": "HyperLiquidWalletTracker/2.0.0"
        }
        request_headers.update(headers)
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                webhook_url, 
                json=content, 
                headers=request_headers,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                if response.status in [200, 201, 202, 204]:
                    logger.info("Webhook notification sent successfully")
                    return True
                else:
                    error_text = await response.text()
                    logger.error(f"Webhook notification failed: {response.status} - {error_text}")
                    return False
                    
    except asyncio.TimeoutError:
        logger.error("Webhook notification timeout")
        return False
    except Exception as e:
        logger.error(f"Error sending webhook notification: {e}")
        return False


def validate_webhook_url(url: str) -> bool:
    """
    Validate webhook URL format.
    
    Args:
        url: URL to validate
        
    Returns:
        True if valid, False otherwise
    """
    try:
        parsed = urlparse(url)
        return parsed.scheme in ["http", "https"] and parsed.netloc
    except Exception:
        return False


def validate_discord_webhook(url: str) -> bool:
    """
    Validate Discord webhook URL format.
    
    Args:
        url: Discord webhook URL to validate
        
    Returns:
        True if valid Discord webhook URL, False otherwise
    """
    if not validate_webhook_url(url):
        return False
    
    return "discord.com" in url or "discordapp.com" in url


def validate_telegram_config(bot_token: str, chat_id: str) -> bool:
    """
    Validate Telegram configuration.
    
    Args:
        bot_token: Telegram bot token
        chat_id: Telegram chat ID
        
    Returns:
        True if configuration appears valid, False otherwise
    """
    if not bot_token or not chat_id:
        return False
    
    # Basic format validation
    if not bot_token.isdigit() or len(bot_token) < 10:
        return False
    
    if not chat_id.startswith("@") and not chat_id.startswith("-"):
        return False
    
    return True


def validate_email_config(email_config: Any) -> bool:
    """
    Validate email configuration.
    
    Args:
        email_config: Email configuration object
        
    Returns:
        True if configuration is valid, False otherwise
    """
    if not email_config.enabled:
        return True  # Not enabled, so valid
    
    required_fields = [
        "smtp_server", "smtp_port", "username", 
        "password", "from_addr", "to_addrs"
    ]
    
    for field in required_fields:
        if not hasattr(email_config, field) or not getattr(email_config, field):
            return False
    
    return True
