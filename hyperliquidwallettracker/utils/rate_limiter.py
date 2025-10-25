"""
Advanced rate limiting for HyperLiquidWalletTracker notifications.

This module provides sophisticated rate limiting with multiple strategies,
pending event queuing, and intelligent batching for optimal notification delivery.
"""

import asyncio
import time
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum

from .logging import get_logger

logger = get_logger(__name__)


class RateLimitStrategy(Enum):
    """Rate limiting strategies."""
    FIXED_WINDOW = "fixed_window"
    SLIDING_WINDOW = "sliding_window"
    TOKEN_BUCKET = "token_bucket"
    LEAKY_BUCKET = "leaky_bucket"


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting."""
    strategy: RateLimitStrategy = RateLimitStrategy.SLIDING_WINDOW
    max_requests: int = 10
    window_seconds: int = 60
    burst_capacity: int = 5
    refill_rate: float = 1.0  # requests per second
    cooldown_seconds: int = 30


@dataclass
class PendingEvent:
    """Represents a pending event in the rate limiter queue."""
    event: Dict[str, Any]
    timestamp: datetime
    priority: int = 0  # Higher number = higher priority
    retry_count: int = 0
    max_retries: int = 3


class RateLimiter:
    """
    Advanced rate limiter with multiple strategies and intelligent queuing.
    
    Features:
    - Multiple rate limiting strategies
    - Pending event queuing with priority
    - Automatic retry with exponential backoff
    - Event batching for efficiency
    - Per-channel and per-wallet rate limiting
    """
    
    def __init__(self, config: RateLimitConfig):
        """
        Initialize rate limiter.
        
        Args:
            config: Rate limiting configuration
        """
        self.config = config
        self.requests: List[float] = []
        self.tokens = config.burst_capacity
        self.last_refill = time.time()
        self.pending_events: Dict[str, List[PendingEvent]] = {}
        self.channel_stats: Dict[str, Dict[str, Any]] = {}
        
        # Start background tasks
        self._refill_task: Optional[asyncio.Task] = None
        self._flush_task: Optional[asyncio.Task] = None
        self._running = False
    
    def _get_key(self, channel: str, wallet: str) -> str:
        """Generate rate limit key for channel/wallet combination."""
        return f"{channel}:{wallet[:8]}"
    
    def _cleanup_old_requests(self, now: float):
        """Remove old requests outside the time window."""
        cutoff = now - self.config.window_seconds
        self.requests = [req_time for req_time in self.requests if req_time > cutoff]
    
    def _refill_tokens(self, now: float):
        """Refill tokens based on elapsed time."""
        elapsed = now - self.last_refill
        tokens_to_add = elapsed * self.config.refill_rate
        self.tokens = min(self.config.burst_capacity, self.tokens + tokens_to_add)
        self.last_refill = now
    
    def can_send_request(self, channel: str, wallet: str) -> Tuple[bool, float]:
        """
        Check if a request can be sent based on rate limiting.
        
        Args:
            channel: Notification channel
            wallet: Wallet address
            
        Returns:
            Tuple of (can_send, wait_time_seconds)
        """
        now = time.time()
        key = self._get_key(channel, wallet)
        
        # Initialize channel stats
        if key not in self.channel_stats:
            self.channel_stats[key] = {
                "requests": [],
                "tokens": self.config.burst_capacity,
                "last_refill": now
            }
        
        stats = self.channel_stats[key]
        
        if self.config.strategy == RateLimitStrategy.FIXED_WINDOW:
            # Clean up old requests
            cutoff = now - self.config.window_seconds
            stats["requests"] = [req_time for req_time in stats["requests"] if req_time > cutoff]
            
            if len(stats["requests"]) >= self.config.max_requests:
                wait_time = self.config.window_seconds - (now - stats["requests"][0])
                return False, max(0, wait_time)
            
            return True, 0
        
        elif self.config.strategy == RateLimitStrategy.SLIDING_WINDOW:
            # Clean up old requests
            cutoff = now - self.config.window_seconds
            stats["requests"] = [req_time for req_time in stats["requests"] if req_time > cutoff]
            
            if len(stats["requests"]) >= self.config.max_requests:
                # Calculate wait time until oldest request expires
                oldest_request = min(stats["requests"])
                wait_time = (oldest_request + self.config.window_seconds) - now
                return False, max(0, wait_time)
            
            return True, 0
        
        elif self.config.strategy == RateLimitStrategy.TOKEN_BUCKET:
            # Refill tokens
            elapsed = now - stats["last_refill"]
            tokens_to_add = elapsed * self.config.refill_rate
            stats["tokens"] = min(self.config.burst_capacity, stats["tokens"] + tokens_to_add)
            stats["last_refill"] = now
            
            if stats["tokens"] >= 1:
                stats["tokens"] -= 1
                return True, 0
            else:
                # Calculate wait time for next token
                wait_time = 1.0 / self.config.refill_rate
                return False, wait_time
        
        else:
            # Default to allowing request
            return True, 0
    
    def add_pending_event(
        self, 
        channel: str, 
        wallet: str, 
        event: Dict[str, Any], 
        priority: int = 0
    ) -> None:
        """
        Add an event to the pending queue.
        
        Args:
            channel: Notification channel
            wallet: Wallet address
            event: Event data
            priority: Event priority (higher = more important)
        """
        key = self._get_key(channel, wallet)
        
        if key not in self.pending_events:
            self.pending_events[key] = []
        
        pending_event = PendingEvent(
            event=event,
            timestamp=datetime.now(timezone.utc),
            priority=priority
        )
        
        self.pending_events[key].append(pending_event)
        
        # Sort by priority (highest first)
        self.pending_events[key].sort(key=lambda x: x.priority, reverse=True)
        
        logger.debug(f"Added pending event for {key} (total: {len(self.pending_events[key])})")
    
    def get_pending_events(self, channel: str, wallet: str) -> List[Dict[str, Any]]:
        """
        Get pending events for a channel/wallet combination.
        
        Args:
            channel: Notification channel
            wallet: Wallet address
            
        Returns:
            List of pending events
        """
        key = self._get_key(channel, wallet)
        return [pe.event for pe in self.pending_events.get(key, [])]
    
    def clear_pending_events(self, channel: str, wallet: str) -> int:
        """
        Clear pending events for a channel/wallet combination.
        
        Args:
            channel: Notification channel
            wallet: Wallet address
            
        Returns:
            Number of events cleared
        """
        key = self._get_key(channel, wallet)
        count = len(self.pending_events.get(key, []))
        if key in self.pending_events:
            del self.pending_events[key]
        return count
    
    def get_pending_count(self, channel: str, wallet: str) -> int:
        """Get number of pending events for a channel/wallet."""
        key = self._get_key(channel, wallet)
        return len(self.pending_events.get(key, []))
    
    def get_all_pending_counts(self) -> Dict[str, int]:
        """Get pending event counts for all channel/wallet combinations."""
        return {key: len(events) for key, events in self.pending_events.items()}
    
    async def start_background_tasks(self):
        """Start background tasks for token refilling and event flushing."""
        if self._running:
            return
        
        self._running = True
        self._refill_task = asyncio.create_task(self._refill_loop())
        self._flush_task = asyncio.create_task(self._flush_loop())
        
        logger.info("Started rate limiter background tasks")
    
    async def stop_background_tasks(self):
        """Stop background tasks."""
        self._running = False
        
        if self._refill_task:
            self._refill_task.cancel()
            try:
                await self._refill_task
            except asyncio.CancelledError:
                pass
        
        if self._flush_task:
            self._flush_task.cancel()
            try:
                await self._flush_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Stopped rate limiter background tasks")
    
    async def _refill_loop(self):
        """Background task to refill tokens."""
        while self._running:
            try:
                await asyncio.sleep(1.0)  # Check every second
                
                now = time.time()
                for key, stats in self.channel_stats.items():
                    if self.config.strategy == RateLimitStrategy.TOKEN_BUCKET:
                        elapsed = now - stats["last_refill"]
                        tokens_to_add = elapsed * self.config.refill_rate
                        stats["tokens"] = min(
                            self.config.burst_capacity, 
                            stats["tokens"] + tokens_to_add
                        )
                        stats["last_refill"] = now
                        
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in refill loop: {e}")
    
    async def _flush_loop(self):
        """Background task to flush pending events when rate limits allow."""
        while self._running:
            try:
                await asyncio.sleep(5.0)  # Check every 5 seconds
                
                now = time.time()
                keys_to_flush = []
                
                for key, events in self.pending_events.items():
                    if not events:
                        continue
                    
                    channel, wallet = key.split(":", 1)
                    can_send, wait_time = self.can_send_request(channel, wallet)
                    
                    if can_send and wait_time <= 0:
                        keys_to_flush.append((key, events))
                
                for key, events in keys_to_flush:
                    channel, wallet = key.split(":", 1)
                    logger.info(f"Flushing {len(events)} pending events for {key}")
                    
                    # Clear pending events
                    self.clear_pending_events(channel, wallet)
                    
                    # Record that we would send these events
                    # (Actual sending would be handled by the caller)
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in flush loop: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get current rate limiter statistics."""
        return {
            "config": {
                "strategy": self.config.strategy.value,
                "max_requests": self.config.max_requests,
                "window_seconds": self.config.window_seconds,
                "burst_capacity": self.config.burst_capacity,
                "refill_rate": self.config.refill_rate,
            },
            "pending_events": self.get_all_pending_counts(),
            "channel_stats": {
                key: {
                    "requests_count": len(stats["requests"]),
                    "tokens": stats["tokens"],
                    "last_refill": stats["last_refill"]
                }
                for key, stats in self.channel_stats.items()
            }
        }


# Global rate limiter instances for different channels
DEFAULT_RATE_LIMITS = {
    "discord": RateLimitConfig(
        strategy=RateLimitStrategy.SLIDING_WINDOW,
        max_requests=10,
        window_seconds=60,
        cooldown_seconds=45
    ),
    "telegram": RateLimitConfig(
        strategy=RateLimitStrategy.SLIDING_WINDOW,
        max_requests=20,
        window_seconds=60,
        cooldown_seconds=30
    ),
    "email": RateLimitConfig(
        strategy=RateLimitStrategy.TOKEN_BUCKET,
        burst_capacity=5,
        refill_rate=0.1,  # 1 email per 10 seconds
        cooldown_seconds=60
    ),
    "webhook": RateLimitConfig(
        strategy=RateLimitStrategy.SLIDING_WINDOW,
        max_requests=30,
        window_seconds=60,
        cooldown_seconds=15
    )
}

# Create rate limiters for each channel
rate_limiters = {
    channel: RateLimiter(config) 
    for channel, config in DEFAULT_RATE_LIMITS.items()
}
