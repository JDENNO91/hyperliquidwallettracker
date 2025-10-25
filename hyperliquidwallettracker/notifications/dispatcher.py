"""
Notification dispatcher for HyperLiquidWalletTracker.

This module provides intelligent notification dispatching with
rate limiting, retry logic, and multi-channel support.
"""

import asyncio
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime, timezone
from dataclasses import dataclass, field

from ..core.config import HyperLiquidConfig
from ..utils.logging import get_logger
from ..utils.rate_limiter import rate_limiters
from ..utils.metrics import metrics_collector
from .channels import (
    send_discord_notification,
    send_telegram_notification,
    send_email_notification,
    send_webhook_notification
)

logger = get_logger(__name__)


@dataclass
class NotificationResult:
    """Result of a notification attempt."""
    channel: str
    success: bool
    error_message: Optional[str] = None
    retry_count: int = 0
    duration_seconds: float = 0.0
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class NotificationDispatcher:
    """
    Intelligent notification dispatcher with rate limiting and retry logic.
    
    Features:
    - Multi-channel notification support
    - Rate limiting per channel
    - Automatic retry with exponential backoff
    - Notification queuing and batching
    - Comprehensive metrics and monitoring
    """
    
    def __init__(self, config: HyperLiquidConfig):
        """
        Initialize notification dispatcher.
        
        Args:
            config: HyperLiquidWalletTracker configuration
        """
        self.config = config
        self.notification_queue: List[Dict[str, Any]] = []
        self.retry_queue: List[Dict[str, Any]] = []
        self.max_retries = 3
        self.retry_delay_base = 5  # seconds
        
        # Channel availability
        self.channel_availability = {
            "discord": config.notifications.discord.enabled,
            "telegram": config.notifications.telegram.enabled,
            "email": config.notifications.email.enabled,
            "webhook": config.notifications.webhook.enabled
        }
        
        # Statistics
        self.stats = {
            "notifications_sent": 0,
            "notifications_failed": 0,
            "retries_attempted": 0,
            "rate_limited": 0,
            "start_time": datetime.now(timezone.utc)
        }
        
        # Background tasks
        self._processing_task: Optional[asyncio.Task] = None
        self._retry_task: Optional[asyncio.Task] = None
        self._running = False
    
    async def start(self):
        """Start the notification dispatcher."""
        if self._running:
            return
        
        self._running = True
        self._processing_task = asyncio.create_task(self._process_queue())
        self._retry_task = asyncio.create_task(self._process_retries())
        
        logger.info("Notification dispatcher started")
    
    async def stop(self):
        """Stop the notification dispatcher."""
        self._running = False
        
        if self._processing_task:
            self._processing_task.cancel()
            try:
                await self._processing_task
            except asyncio.CancelledError:
                pass
        
        if self._retry_task:
            self._retry_task.cancel()
            try:
                await self._retry_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Notification dispatcher stopped")
    
    async def dispatch_notification(self, notification: Dict[str, Any]) -> List[NotificationResult]:
        """
        Dispatch a notification to all enabled channels.
        
        Args:
            notification: Notification to dispatch
            
        Returns:
            List of notification results
        """
        results = []
        
        # Get formatted content
        formatted = notification.get("formatted", {})
        context = notification.get("context")
        
        if not context:
            logger.error("No context in notification")
            return results
        
        wallet = context.wallet
        
        # Send to each enabled channel
        for channel, enabled in self.channel_availability.items():
            if not enabled:
                continue
            
            if channel not in formatted:
                logger.warning(f"No formatted content for channel: {channel}")
                continue
            
            result = await self._send_to_channel(
                channel=channel,
                wallet=wallet,
                content=formatted[channel],
                notification=notification
            )
            
            results.append(result)
        
        return results
    
    async def _send_to_channel(
        self, 
        channel: str, 
        wallet: str, 
        content: Any, 
        notification: Dict[str, Any]
    ) -> NotificationResult:
        """Send notification to a specific channel."""
        start_time = datetime.now(timezone.utc)
        
        try:
            # Check rate limiting
            rate_limiter = rate_limiters.get(channel)
            if rate_limiter:
                can_send, wait_time = rate_limiter.can_send_request(channel, wallet)
                if not can_send:
                    # Add to pending queue
                    rate_limiter.add_pending_event(channel, wallet, notification)
                    self.stats["rate_limited"] += 1
                    
                    return NotificationResult(
                        channel=channel,
                        success=False,
                        error_message=f"Rate limited, waiting {wait_time:.1f}s"
                    )
            
            # Send notification
            success = await self._send_notification_to_channel(channel, content)
            
            duration = (datetime.now(timezone.utc) - start_time).total_seconds()
            
            if success:
                self.stats["notifications_sent"] += 1
                metrics_collector.record_notification_sent(channel, "success", duration)
                
                return NotificationResult(
                    channel=channel,
                    success=True,
                    duration_seconds=duration
                )
            else:
                self.stats["notifications_failed"] += 1
                metrics_collector.record_notification_sent(channel, "error", duration)
                
                # Add to retry queue
                await self._add_to_retry_queue(channel, wallet, content, notification)
                
                return NotificationResult(
                    channel=channel,
                    success=False,
                    error_message="Notification failed"
                )
                
        except Exception as e:
            duration = (datetime.now(timezone.utc) - start_time).total_seconds()
            logger.error(f"Error sending {channel} notification: {e}")
            
            self.stats["notifications_failed"] += 1
            metrics_collector.record_notification_sent(channel, "error", duration)
            
            # Add to retry queue
            await self._add_to_retry_queue(channel, wallet, content, notification)
            
            return NotificationResult(
                channel=channel,
                success=False,
                error_message=str(e),
                duration_seconds=duration
            )
    
    async def _send_notification_to_channel(self, channel: str, content: Any) -> bool:
        """Send notification to specific channel implementation."""
        try:
            if channel == "discord":
                return await send_discord_notification(
                    self.config.notifications.discord.webhook_url,
                    content
                )
            elif channel == "telegram":
                return await send_telegram_notification(
                    self.config.notifications.telegram.bot_token,
                    self.config.notifications.telegram.chat_id,
                    content
                )
            elif channel == "email":
                return await send_email_notification(
                    self.config.notifications.email,
                    content
                )
            elif channel == "webhook":
                return await send_webhook_notification(
                    self.config.notifications.webhook.url,
                    self.config.notifications.webhook.headers,
                    content
                )
            else:
                logger.error(f"Unknown channel: {channel}")
                return False
                
        except Exception as e:
            logger.error(f"Error in {channel} notification: {e}")
            return False
    
    async def _add_to_retry_queue(
        self, 
        channel: str, 
        wallet: str, 
        content: Any, 
        notification: Dict[str, Any]
    ):
        """Add notification to retry queue."""
        retry_item = {
            "channel": channel,
            "wallet": wallet,
            "content": content,
            "notification": notification,
            "retry_count": 0,
            "next_retry": datetime.now(timezone.utc).timestamp() + self.retry_delay_base,
            "created_at": datetime.now(timezone.utc)
        }
        
        self.retry_queue.append(retry_item)
        logger.debug(f"Added {channel} notification to retry queue")
    
    async def _process_queue(self):
        """Background task to process notification queue."""
        while self._running:
            try:
                await asyncio.sleep(1.0)  # Check every second
                
                # Process any queued notifications
                if self.notification_queue:
                    notification = self.notification_queue.pop(0)
                    await self.dispatch_notification(notification)
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in notification processing: {e}")
    
    async def _process_retries(self):
        """Background task to process retry queue."""
        while self._running:
            try:
                await asyncio.sleep(5.0)  # Check every 5 seconds
                
                now = datetime.now(timezone.utc)
                retry_items = []
                
                # Find items ready for retry
                for item in self.retry_queue:
                    if (item["retry_count"] < self.max_retries and 
                        now.timestamp() >= item["next_retry"]):
                        retry_items.append(item)
                
                # Process retry items
                for item in retry_items:
                    self.retry_queue.remove(item)
                    item["retry_count"] += 1
                    self.stats["retries_attempted"] += 1
                    
                    # Calculate next retry time with exponential backoff
                    delay = self.retry_delay_base * (2 ** item["retry_count"])
                    item["next_retry"] = now.timestamp() + delay
                    
                    # Try sending again
                    success = await self._send_notification_to_channel(
                        item["channel"], 
                        item["content"]
                    )
                    
                    if success:
                        logger.info(f"Retry successful for {item['channel']} notification")
                        self.stats["notifications_sent"] += 1
                    else:
                        if item["retry_count"] < self.max_retries:
                            # Add back to retry queue
                            self.retry_queue.append(item)
                            logger.debug(f"Scheduled retry {item['retry_count']} for {item['channel']}")
                        else:
                            logger.error(f"Max retries exceeded for {item['channel']} notification")
                            self.stats["notifications_failed"] += 1
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in retry processing: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get notification dispatcher statistics."""
        uptime = datetime.now(timezone.utc) - self.stats["start_time"]
        
        return {
            "dispatcher_stats": {
                "notifications_sent": self.stats["notifications_sent"],
                "notifications_failed": self.stats["notifications_failed"],
                "retries_attempted": self.stats["retries_attempted"],
                "rate_limited": self.stats["rate_limited"],
                "uptime_seconds": uptime.total_seconds(),
                "success_rate": (
                    self.stats["notifications_sent"] / 
                    max(1, self.stats["notifications_sent"] + self.stats["notifications_failed"])
                )
            },
            "queue_status": {
                "notification_queue_size": len(self.notification_queue),
                "retry_queue_size": len(self.retry_queue)
            },
            "channel_availability": self.channel_availability.copy()
        }
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get health status of the notification dispatcher."""
        success_rate = (
            self.stats["notifications_sent"] / 
            max(1, self.stats["notifications_sent"] + self.stats["notifications_failed"])
        )
        
        return {
            "status": "healthy" if success_rate > 0.8 else "degraded",
            "success_rate": success_rate,
            "notifications_sent": self.stats["notifications_sent"],
            "notifications_failed": self.stats["notifications_failed"],
            "retry_queue_size": len(self.retry_queue),
            "enabled_channels": sum(self.channel_availability.values()),
            "total_channels": len(self.channel_availability)
        }
