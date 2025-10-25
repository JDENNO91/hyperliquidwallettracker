"""
Modern WebSocket client for HyperLiquidWalletTracker with enhanced reliability and monitoring.

This module provides a robust WebSocket client with automatic reconnection,
health monitoring, and comprehensive error handling.
"""

import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from typing import Dict, Set, Optional, Callable, Any
from datetime import datetime, timezone

import websockets
from websockets.exceptions import ConnectionClosed, WebSocketException

from .config import HyperLiquidConfig
from ..utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class ConnectionStats:
    """Connection statistics and health metrics."""
    connected: bool = False
    total_messages: int = 0
    successful_parses: int = 0
    failed_parses: int = 0
    last_message_time: Optional[datetime] = None
    reconnect_count: int = 0
    subscription_count: int = 0
    start_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    wallet_events: Dict[str, int] = field(default_factory=dict)
    last_health_check: Optional[datetime] = None
    consecutive_failures: int = 0


class WebSocketClient:
    """
    Modern WebSocket client with enhanced reliability and monitoring.
    
    Features:
    - Automatic reconnection with exponential backoff
    - Health monitoring and connection validation
    - Comprehensive statistics tracking
    - Graceful shutdown handling
    - Event-driven architecture
    """
    
    def __init__(
        self,
        config: HyperLiquidConfig,
        event_handler: Optional[Callable[[Dict[str, Any]], None]] = None
    ):
        """
        Initialize WebSocket client.
        
        Args:
            config: HyperLiquidWalletTracker configuration
            event_handler: Optional callback for processing events
        """
        self.config = config
        self.event_handler = event_handler
        self.websocket: Optional[websockets.WebSocketClientProtocol] = None
        self.stats = ConnectionStats()
        self.is_shutting_down = False
        self.health_check_task: Optional[asyncio.Task] = None
        self.subscribed_wallets: Set[str] = set()
        self.wallet_subscriptions: Dict[str, Set[str]] = {}
        
        # Initialize wallet tracking
        for wallet in config.watched_wallets:
            self.stats.wallet_events[wallet] = 0
    
    async def connect(self) -> bool:
        """
        Establish WebSocket connection.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            logger.info(f"Connecting to {self.config.websocket_url}")
            
            self.websocket = await websockets.connect(
                self.config.websocket_url,
                ping_interval=None,  # Disable automatic ping
                ping_timeout=None,
                close_timeout=5,
                max_size=10**7,
                compression=None
            )
            
            self.stats.connected = True
            self.stats.reconnect_count += 1
            self.stats.consecutive_failures = 0
            
            logger.info("WebSocket connected successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to WebSocket: {e}")
            self.stats.connected = False
            self.stats.consecutive_failures += 1
            return False
    
    async def subscribe_to_wallet(self, wallet: str, channel_type: str) -> bool:
        """
        Subscribe to specific wallet channel.
        
        Args:
            wallet: Wallet address to subscribe to
            channel_type: Type of channel (userFills, userEvents, orderUpdates)
            
        Returns:
            True if subscription successful, False otherwise
        """
        if not self.websocket or self.websocket.closed:
            logger.error("WebSocket not connected, cannot subscribe")
            return False
        
        sub_key = f"{channel_type}:{wallet}"
        if sub_key in self.subscribed_wallets:
            return True
        
        try:
            subscription_msg = {
                "method": "subscribe",
                "subscription": {"type": channel_type, "user": wallet}
            }
            
            await self.websocket.send(json.dumps(subscription_msg))
            self.subscribed_wallets.add(sub_key)
            
            if channel_type not in self.wallet_subscriptions:
                self.wallet_subscriptions[channel_type] = set()
            self.wallet_subscriptions[channel_type].add(wallet)
            
            self.stats.subscription_count += 1
            logger.info(f"Subscribed to {channel_type} for wallet: {wallet[:8]}...")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to subscribe {channel_type} for {wallet[:8]}: {e}")
            return False
    
    async def subscribe_to_all_wallets(self) -> bool:
        """
        Subscribe to all configured wallets.
        
        Returns:
            True if at least one subscription successful, False otherwise
        """
        if not self.websocket or self.websocket.closed:
            logger.error("WebSocket not connected, cannot subscribe")
            return False
        
        channel_types = ["userFills", "userEvents", "orderUpdates"]
        success_count = 0
        total_subscriptions = len(self.config.watched_wallets) * len(channel_types)
        
        logger.info(f"Setting up {total_subscriptions} subscriptions...")
        
        for wallet in self.config.watched_wallets:
            for channel_type in channel_types:
                success = await self.subscribe_to_wallet(wallet, channel_type)
                if success:
                    success_count += 1
                await asyncio.sleep(0.3)  # Rate limiting
        
        logger.info(f"Subscription complete: {success_count}/{total_subscriptions} successful")
        return success_count > 0
    
    async def health_check(self) -> bool:
        """
        Perform health check on WebSocket connection.
        
        Returns:
            True if connection is healthy, False otherwise
        """
        try:
            if not self.websocket or self.websocket.closed:
                return False
            
            # Send ping message
            ping_message = {
                "method": "ping",
                "id": int(time.time() * 1000)
            }
            
            await self.websocket.send(json.dumps(ping_message))
            await asyncio.sleep(0.1)  # Allow response
            
            self.stats.last_health_check = datetime.now(timezone.utc)
            return True
            
        except Exception as e:
            logger.debug(f"Health check failed: {e}")
            return False
    
    async def connection_monitor(self):
        """Monitor connection health and trigger reconnection if needed."""
        while not self.is_shutting_down:
            try:
                check_interval = min(30, 5 + self.stats.consecutive_failures * 2)
                await asyncio.sleep(check_interval)
                
                if not await self.health_check():
                    self.stats.consecutive_failures += 1
                    
                    if self.stats.consecutive_failures >= 2:
                        logger.warning(f"Connection unhealthy for {self.stats.consecutive_failures} checks")
                        if self.websocket and not self.websocket.closed:
                            await self.websocket.close(code=1000, reason="Health check failed")
                        break
                else:
                    if self.stats.consecutive_failures > 0:
                        logger.info("Connection recovered")
                    self.stats.consecutive_failures = 0
                
                # Log statistics every 5 minutes
                uptime = datetime.now(timezone.utc) - self.stats.start_time
                if uptime.total_seconds() > 300 and uptime.total_seconds() % 300 < check_interval:
                    logger.info(
                        f"Stats: {self.stats.total_messages} msgs, "
                        f"{self.stats.successful_parses} parsed, "
                        f"{self.stats.subscription_count} subs, "
                        f"uptime: {uptime.total_seconds()/60:.1f}m"
                    )
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Connection monitor error: {e}")
    
    async def handle_message(self, message: str):
        """
        Handle incoming WebSocket message.
        
        Args:
            message: Raw message from WebSocket
        """
        try:
            self.stats.total_messages += 1
            self.stats.last_message_time = datetime.now(timezone.utc)
            
            raw_event = json.loads(message)
            channel = raw_event.get("channel", "unknown")
            
            if channel == "error":
                error_msg = raw_event.get("data", "Unknown error")
                logger.error(f"Server Error: {error_msg}")
                return
            
            elif channel == "subscriptionResponse":
                await self._handle_subscription_response(raw_event)
                return
            
            elif channel in ["userFills", "userEvents", "orderUpdates"]:
                await self._handle_wallet_event(raw_event, channel)
            
            else:
                logger.debug(f"General event on {channel}")
                
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON received: {e}")
        except Exception as e:
            logger.error(f"Error handling message: {e}")
    
    async def _handle_subscription_response(self, raw_event: Dict[str, Any]):
        """Handle subscription response messages."""
        response_data = raw_event.get("data", {})
        if isinstance(response_data, dict):
            success = response_data.get("success", True)
            if success:
                logger.debug("Subscription confirmed")
            else:
                error = response_data.get("error", "Unknown subscription error")
                logger.error(f"Subscription failed: {error}")
    
    async def _handle_wallet_event(self, raw_event: Dict[str, Any], channel: str):
        """Handle wallet-specific events."""
        event_data = raw_event.get("data")
        wallet = (
            raw_event.get("user") or
            raw_event.get("wallet") or
            self._extract_wallet_from_event(event_data, raw_event)
        )
        
        if not wallet or wallet not in self.config.watched_wallets:
            logger.debug(f"Filtering out event from non-watched wallet: {wallet}")
            return
        
        # Update wallet statistics
        if wallet in self.stats.wallet_events:
            self.stats.wallet_events[wallet] += 1
        
        logger.debug(f"Processing {channel} for wallet: {wallet[:8]}...")
        
        try:
            if isinstance(event_data, list):
                for i, single_event in enumerate(event_data):
                    await self._process_single_event(single_event, channel, wallet, f"{channel}_{i}")
            elif isinstance(event_data, dict):
                await self._process_single_event(event_data, channel, wallet, channel)
            else:
                logger.warning(f"Unexpected event data format on {channel}: {type(event_data)}")
                
        except Exception as e:
            logger.error(f"Error processing {channel} event: {e}")
    
    async def _process_single_event(
        self, 
        event_data: Dict[str, Any], 
        channel: str, 
        wallet: str, 
        event_id: str
    ):
        """Process a single event."""
        try:
            if not isinstance(event_data, dict):
                logger.warning(f"Event {event_id} is not a dict: {type(event_data)}")
                return
            
            # Create event object
            event = {
                "type": channel,
                "wallet": wallet,
                "data": event_data,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "raw": event_data
            }
            
            self.stats.successful_parses += 1
            
            # Call event handler if provided
            if self.event_handler:
                await self.event_handler(event)
            
            logger.info(f"Processed {len([event])} event(s) for {wallet[:8]}... on {channel}")
            
        except Exception as e:
            self.stats.failed_parses += 1
            logger.error(f"Error processing event {event_id} for {wallet[:8]}: {e}")
    
    def _extract_wallet_from_event(self, event_data: Any, raw_event: Dict[str, Any]) -> Optional[str]:
        """Extract wallet address from event data."""
        wallet_fields = ['user', 'wallet', 'address', 'account', 'from', 'to', 'owner', 'trader', 'userAddress']
        
        def check_dict_for_wallet(data: Dict[str, Any], source_name: str) -> Optional[str]:
            if not isinstance(data, dict):
                return None
            for field in wallet_fields:
                if field in data and data[field]:
                    wallet = str(data[field]).strip()
                    if wallet and wallet not in ['unknown', 'multiple_wallets', '0x0', 'null']:
                        return wallet
            return None
        
        # Check raw_event first
        wallet = check_dict_for_wallet(raw_event, 'raw_event')
        if wallet:
            return wallet
        
        # Check event_data
        if isinstance(event_data, list) and event_data:
            wallet = check_dict_for_wallet(event_data[0], 'event_data[0]')
        elif isinstance(event_data, dict):
            wallet = check_dict_for_wallet(event_data, 'event_data')
            
            if not wallet:
                nested_data = event_data.get('data')
                if nested_data:
                    wallet = check_dict_for_wallet(nested_data, 'nested_data')
        
        return wallet
    
    async def run(self):
        """Main connection and message processing loop."""
        self.stats.start_time = datetime.now(timezone.utc)
        
        logger.info(f"Starting HyperLiquidWalletTracker for {len(self.config.watched_wallets)} wallets:")
        for wallet in self.config.watched_wallets:
            logger.info(f"  └── Watching: {wallet[:8]}...")
        
        while not self.is_shutting_down:
            try:
                if await self.connect():
                    # Start health monitoring
                    if not self.health_check_task or self.health_check_task.done():
                        self.health_check_task = asyncio.create_task(self.connection_monitor())
                    
                    # Subscribe to wallets
                    if await self.subscribe_to_all_wallets():
                        logger.info("Listening for events...")
                        
                        # Message processing loop
                        async for message in self.websocket:
                            await self.handle_message(message)
                    else:
                        logger.error("Failed to establish subscriptions")
                        continue
                        
            except (ConnectionClosed, WebSocketException) as e:
                logger.warning(f"WebSocket error: {e}")
                self.stats.connected = False
                self.stats.consecutive_failures += 1
                
            except Exception as e:
                logger.error(f"Unexpected connection error: {e}")
                self.stats.connected = False
                self.stats.consecutive_failures += 1
                
            finally:
                self.stats.connected = False
                if self.health_check_task and not self.health_check_task.done():
                    self.health_check_task.cancel()
                    try:
                        await self.health_check_task
                    except asyncio.CancelledError:
                        pass
            
            if not self.is_shutting_down:
                # Progressive backoff
                if self.stats.consecutive_failures <= 3:
                    reconnect_delay = 2
                elif self.stats.consecutive_failures <= 10:
                    reconnect_delay = 5
                else:
                    reconnect_delay = min(30, self.stats.consecutive_failures)
                
                if self.stats.consecutive_failures <= 5:
                    logger.info(f"Reconnecting in {reconnect_delay} seconds... (attempt {self.stats.consecutive_failures})")
                
                await asyncio.sleep(reconnect_delay)
    
    async def shutdown(self):
        """Graceful shutdown of WebSocket client."""
        logger.info("Shutting down WebSocket client...")
        self.is_shutting_down = True
        
        if self.health_check_task and not self.health_check_task.done():
            self.health_check_task.cancel()
            try:
                await self.health_check_task
            except asyncio.CancelledError:
                pass
        
        if self.websocket and not self.websocket.closed:
            try:
                await self.websocket.close(code=1000, reason="Graceful shutdown")
            except:
                pass
        
        logger.info("WebSocket client shutdown complete")
