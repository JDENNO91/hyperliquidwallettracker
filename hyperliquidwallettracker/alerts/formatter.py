"""
Notification formatter for HyperLiquidWalletTracker.

This module provides rich formatting for notifications across different
channels with emojis, formatting, and contextual information.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from dataclasses import dataclass

from .classifier import PositionSize
from ..utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class NotificationContext:
    """Context information for notification formatting."""
    wallet: str
    event_type: str
    position_size: Optional[PositionSize] = None
    usd_value: Optional[float] = None
    coin: Optional[str] = None
    side: Optional[str] = None
    timestamp: Optional[datetime] = None
    additional_data: Dict[str, Any] = None


class NotificationFormatter:
    """
    Rich notification formatter with channel-specific formatting.
    
    Features:
    - Channel-specific formatting (Discord, Telegram, Email, Webhook)
    - Rich text with emojis and formatting
    - Contextual information
    - Position size indicators
    - Market context
    """
    
    def __init__(self):
        """Initialize notification formatter."""
        self.emoji_map = {
            PositionSize.WHALE: "🐋",
            PositionSize.LARGE: "🦈", 
            PositionSize.MEDIUM: "🐟",
            PositionSize.NOTABLE: "🦐",
            PositionSize.SMALL: "🐠"
        }
        
        self.severity_emojis = {
            "critical": "🚨",
            "high": "⚠️",
            "medium": "📊",
            "low": "👀",
            "info": "ℹ️"
        }
    
    def format_discord_notification(
        self, 
        context: NotificationContext, 
        event: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Format notification for Discord.
        
        Args:
            context: Notification context
            event: Event data
            
        Returns:
            Discord webhook payload
        """
        # Create embed
        embed = {
            "title": self._get_title(context),
            "description": self._get_description(context, event),
            "color": self._get_color(context),
            "timestamp": (context.timestamp or datetime.now(timezone.utc)).isoformat(),
            "fields": self._get_discord_fields(context, event),
            "footer": {
                "text": f"HyperLiquidWalletTracker • {context.wallet[:8]}..."
            }
        }
        
        # Add thumbnail if available
        if context.coin:
            embed["thumbnail"] = {
                "url": f"https://cryptoicons.org/api/color/{context.coin.lower()}/200"
            }
        
        return {
            "username": "HyperLiquid Tracker",
            "avatar_url": "https://hyperliquid.xyz/favicon.ico",
            "embeds": [embed]
        }
    
    def format_telegram_notification(
        self, 
        context: NotificationContext, 
        event: Dict[str, Any]
    ) -> str:
        """
        Format notification for Telegram.
        
        Args:
            context: Notification context
            event: Event data
            
        Returns:
            Formatted Telegram message
        """
        lines = []
        
        # Header with emoji
        emoji = self.emoji_map.get(context.position_size, "📊")
        lines.append(f"{emoji} *{self._get_title(context)}*")
        lines.append("")
        
        # Main description
        lines.append(self._get_description(context, event))
        lines.append("")
        
        # Details
        if context.usd_value:
            lines.append(f"💰 *Value:* ${context.usd_value:,.2f}")
        
        if context.coin:
            lines.append(f"🪙 *Coin:* {context.coin}")
        
        if context.side:
            side_emoji = "📈" if context.side.lower() in ["buy", "long"] else "📉"
            lines.append(f"{side_emoji} *Side:* {context.side.upper()}")
        
        lines.append(f"🔗 *Wallet:* `{context.wallet[:8]}...`")
        
        # Timestamp
        timestamp = context.timestamp or datetime.now(timezone.utc)
        lines.append(f"⏰ *Time:* {timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}")
        
        return "\n".join(lines)
    
    def format_email_notification(
        self, 
        context: NotificationContext, 
        event: Dict[str, Any]
    ) -> Dict[str, str]:
        """
        Format notification for email.
        
        Args:
            context: Notification context
            event: Event data
            
        Returns:
            Email content (subject, html_body, text_body)
        """
        subject = f"HyperLiquid Alert: {self._get_title(context)}"
        
        # HTML body
        html_body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                        color: white; padding: 20px; border-radius: 8px 8px 0 0;">
                <h1 style="margin: 0; font-size: 24px;">
                    {self.emoji_map.get(context.position_size, "📊")} {self._get_title(context)}
                </h1>
            </div>
            
            <div style="background: #f8f9fa; padding: 20px; border-radius: 0 0 8px 8px;">
                <p style="font-size: 16px; margin: 0 0 20px 0;">
                    {self._get_description(context, event)}
                </p>
                
                <div style="background: white; padding: 15px; border-radius: 6px; margin: 10px 0;">
                    <h3 style="margin: 0 0 10px 0; color: #333;">Position Details</h3>
                    <table style="width: 100%; border-collapse: collapse;">
                        <tr>
                            <td style="padding: 8px; border-bottom: 1px solid #eee; font-weight: bold;">Value:</td>
                            <td style="padding: 8px; border-bottom: 1px solid #eee;">${context.usd_value:,.2f}</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px; border-bottom: 1px solid #eee; font-weight: bold;">Coin:</td>
                            <td style="padding: 8px; border-bottom: 1px solid #eee;">{context.coin or 'N/A'}</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px; border-bottom: 1px solid #eee; font-weight: bold;">Side:</td>
                            <td style="padding: 8px; border-bottom: 1px solid #eee;">{context.side or 'N/A'}</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px; border-bottom: 1px solid #eee; font-weight: bold;">Wallet:</td>
                            <td style="padding: 8px; border-bottom: 1px solid #eee;">{context.wallet[:8]}...</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px; font-weight: bold;">Time:</td>
                            <td style="padding: 8px;">{(context.timestamp or datetime.now(timezone.utc)).strftime('%Y-%m-%d %H:%M:%S UTC')}</td>
                        </tr>
                    </table>
                </div>
                
                <div style="margin-top: 20px; padding: 15px; background: #e3f2fd; border-radius: 6px;">
                    <p style="margin: 0; font-size: 14px; color: #1976d2;">
                        <strong>HyperLiquidWalletTracker</strong> - Advanced wallet monitoring system
                    </p>
                </div>
            </div>
        </body>
        </html>
        """
        
        # Text body
        text_body = f"""
{self._get_title(context)}

{self._get_description(context, event)}

Position Details:
- Value: ${context.usd_value:,.2f}
- Coin: {context.coin or 'N/A'}
- Side: {context.side or 'N/A'}
- Wallet: {context.wallet[:8]}...
- Time: {(context.timestamp or datetime.now(timezone.utc)).strftime('%Y-%m-%d %H:%M:%S UTC')}

HyperLiquidWalletTracker - Advanced wallet monitoring system
        """.strip()
        
        return {
            "subject": subject,
            "html_body": html_body,
            "text_body": text_body
        }
    
    def format_webhook_notification(
        self, 
        context: NotificationContext, 
        event: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Format notification for webhook.
        
        Args:
            context: Notification context
            event: Event data
            
        Returns:
            Webhook payload
        """
        return {
            "alert_type": "hyperliquid_wallet_activity",
            "severity": self._get_severity(context),
            "title": self._get_title(context),
            "description": self._get_description(context, event),
            "timestamp": (context.timestamp or datetime.now(timezone.utc)).isoformat(),
            "data": {
                "wallet": context.wallet,
                "event_type": context.event_type,
                "position_size": context.position_size.value if context.position_size else None,
                "usd_value": context.usd_value,
                "coin": context.coin,
                "side": context.side,
                "raw_event": event
            },
            "metadata": {
                "source": "HyperLiquidWalletTracker",
                "version": "2.0.0",
                "monitoring_system": "hyperliquid"
            }
        }
    
    def _get_title(self, context: NotificationContext) -> str:
        """Get notification title."""
        if context.position_size:
            emoji = self.emoji_map.get(context.position_size, "📊")
            return f"{emoji} {context.position_size.value} Position Alert"
        else:
            return "📊 HyperLiquid Activity Alert"
    
    def _get_description(self, context: NotificationContext, event: Dict[str, Any]) -> str:
        """Get notification description."""
        if context.position_size and context.usd_value:
            return f"Detected {context.position_size.value.lower()} position worth ${context.usd_value:,.2f}"
        elif context.usd_value:
            return f"Position detected worth ${context.usd_value:,.2f}"
        else:
            return f"Activity detected on wallet {context.wallet[:8]}..."
    
    def _get_color(self, context: NotificationContext) -> int:
        """Get Discord embed color based on position size."""
        color_map = {
            PositionSize.WHALE: 0xff0000,  # Red
            PositionSize.LARGE: 0xff6600,  # Orange
            PositionSize.MEDIUM: 0xffcc00,  # Yellow
            PositionSize.NOTABLE: 0x00ccff,  # Light blue
            PositionSize.SMALL: 0x00ff00   # Green
        }
        return color_map.get(context.position_size, 0x666666)
    
    def _get_severity(self, context: NotificationContext) -> str:
        """Get severity level based on position size."""
        severity_map = {
            PositionSize.WHALE: "critical",
            PositionSize.LARGE: "high",
            PositionSize.MEDIUM: "medium",
            PositionSize.NOTABLE: "low",
            PositionSize.SMALL: "info"
        }
        return severity_map.get(context.position_size, "info")
    
    def _get_discord_fields(self, context: NotificationContext, event: Dict[str, Any]) -> List[Dict[str, str]]:
        """Get Discord embed fields."""
        fields = []
        
        if context.usd_value:
            fields.append({
                "name": "💰 Value",
                "value": f"${context.usd_value:,.2f}",
                "inline": True
            })
        
        if context.coin:
            fields.append({
                "name": "🪙 Coin",
                "value": context.coin,
                "inline": True
            })
        
        if context.side:
            side_emoji = "📈" if context.side.lower() in ["buy", "long"] else "📉"
            fields.append({
                "name": f"{side_emoji} Side",
                "value": context.side.upper(),
                "inline": True
            })
        
        fields.append({
            "name": "🔗 Wallet",
            "value": f"`{context.wallet[:8]}...`",
            "inline": True
        })
        
        if context.position_size:
            fields.append({
                "name": "📊 Classification",
                "value": context.position_size.value,
                "inline": True
            })
        
        return fields
