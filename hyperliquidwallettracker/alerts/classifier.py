"""
Position classification system for HyperLiquidWalletTracker.

This module provides intelligent position classification based on USD value
with configurable thresholds and additional context analysis.
"""

from typing import Optional, Dict, Any
from dataclasses import dataclass
from enum import Enum

from ..core.config import PositionThresholds
from ..utils.logging import get_logger

logger = get_logger(__name__)


class PositionSize(Enum):
    """Position size classifications."""
    WHALE = "WHALE"
    LARGE = "LARGE" 
    MEDIUM = "MEDIUM"
    NOTABLE = "NOTABLE"
    SMALL = "SMALL"


@dataclass
class PositionAnalysis:
    """Analysis of a position including classification and context."""
    size_class: PositionSize
    usd_value: float
    confidence: float  # 0.0 to 1.0
    factors: Dict[str, Any]
    recommendation: Optional[str] = None


class PositionClassifier:
    """
    Intelligent position classifier with configurable thresholds.
    
    Features:
    - USD value-based classification
    - Confidence scoring
    - Context analysis
    - Market impact assessment
    - Trend analysis
    """
    
    def __init__(self, thresholds: PositionThresholds):
        """
        Initialize position classifier.
        
        Args:
            thresholds: Position size thresholds
        """
        self.thresholds = thresholds
        self.classification_history: Dict[str, list] = {}
    
    def classify_position(self, event: Dict[str, Any]) -> Optional[PositionSize]:
        """
        Classify a position based on event data.
        
        Args:
            event: Event data containing position information
            
        Returns:
            Position size classification or None if not applicable
        """
        try:
            # Extract USD value
            usd_value = self._extract_usd_value(event)
            if usd_value is None or usd_value <= 0:
                return None
            
            # Classify based on thresholds
            if usd_value >= self.thresholds.whale_threshold:
                return PositionSize.WHALE
            elif usd_value >= self.thresholds.large_threshold:
                return PositionSize.LARGE
            elif usd_value >= self.thresholds.medium_threshold:
                return PositionSize.MEDIUM
            elif usd_value >= self.thresholds.notable_threshold:
                return PositionSize.NOTABLE
            else:
                return PositionSize.SMALL
                
        except Exception as e:
            logger.error(f"Error classifying position: {e}")
            return None
    
    def analyze_position(self, event: Dict[str, Any]) -> Optional[PositionAnalysis]:
        """
        Perform comprehensive position analysis.
        
        Args:
            event: Event data containing position information
            
        Returns:
            Detailed position analysis or None if not applicable
        """
        try:
            # Extract basic information
            usd_value = self._extract_usd_value(event)
            if usd_value is None or usd_value <= 0:
                return None
            
            # Classify position
            size_class = self.classify_position(event)
            if size_class is None:
                return None
            
            # Calculate confidence
            confidence = self._calculate_confidence(event, usd_value)
            
            # Analyze factors
            factors = self._analyze_factors(event, usd_value)
            
            # Generate recommendation
            recommendation = self._generate_recommendation(size_class, usd_value, factors)
            
            return PositionAnalysis(
                size_class=size_class,
                usd_value=usd_value,
                confidence=confidence,
                factors=factors,
                recommendation=recommendation
            )
            
        except Exception as e:
            logger.error(f"Error analyzing position: {e}")
            return None
    
    def _extract_usd_value(self, event: Dict[str, Any]) -> Optional[float]:
        """Extract USD value from event data."""
        # Try different field names for USD value
        usd_fields = [
            "usd_value", "usdValue", "value_usd", "valueUSD",
            "total_value", "totalValue", "amount_usd", "amountUSD"
        ]
        
        for field in usd_fields:
            if field in event and event[field] is not None:
                try:
                    return float(event[field])
                except (ValueError, TypeError):
                    continue
        
        # Try to calculate from price and size
        price = self._extract_price(event)
        size = self._extract_size(event)
        
        if price is not None and size is not None:
            return float(price) * float(size)
        
        return None
    
    def _extract_price(self, event: Dict[str, Any]) -> Optional[float]:
        """Extract price from event data."""
        price_fields = ["price", "limitPx", "limit_px", "execution_price"]
        
        for field in price_fields:
            if field in event and event[field] is not None:
                try:
                    return float(event[field])
                except (ValueError, TypeError):
                    continue
        
        return None
    
    def _extract_size(self, event: Dict[str, Any]) -> Optional[float]:
        """Extract size from event data."""
        size_fields = ["size", "sz", "quantity", "amount", "volume"]
        
        for field in size_fields:
            if field in event and event[field] is not None:
                try:
                    return float(event[field])
                except (ValueError, TypeError):
                    continue
        
        return None
    
    def _calculate_confidence(self, event: Dict[str, Any], usd_value: float) -> float:
        """Calculate confidence score for position classification."""
        confidence = 1.0
        
        # Reduce confidence if price or size is missing
        if self._extract_price(event) is None or self._extract_size(event) is None:
            confidence *= 0.8
        
        # Reduce confidence for very small values
        if usd_value < 100:
            confidence *= 0.6
        
        # Increase confidence for whale positions
        if usd_value >= self.thresholds.whale_threshold:
            confidence = min(1.0, confidence * 1.2)
        
        return max(0.0, min(1.0, confidence))
    
    def _analyze_factors(self, event: Dict[str, Any], usd_value: float) -> Dict[str, Any]:
        """Analyze additional factors that might affect the position."""
        factors = {
            "usd_value": usd_value,
            "coin": event.get("coin", "unknown"),
            "side": event.get("side", "unknown"),
            "order_type": event.get("orderType", "unknown"),
            "has_price": self._extract_price(event) is not None,
            "has_size": self._extract_size(event) is not None,
        }
        
        # Add market context if available
        if "market_data" in event:
            market_data = event["market_data"]
            factors.update({
                "market_cap": market_data.get("market_cap"),
                "volume_24h": market_data.get("volume_24h"),
                "price_change_24h": market_data.get("price_change_24h"),
            })
        
        # Add timing context
        if "timestamp" in event:
            factors["timestamp"] = event["timestamp"]
        
        return factors
    
    def _generate_recommendation(
        self, 
        size_class: PositionSize, 
        usd_value: float, 
        factors: Dict[str, Any]
    ) -> str:
        """Generate recommendation based on position analysis."""
        coin = factors.get("coin", "unknown")
        
        if size_class == PositionSize.WHALE:
            return f"🚨 WHALE ALERT: ${usd_value:,.0f} {coin} position detected - Monitor closely for market impact"
        
        elif size_class == PositionSize.LARGE:
            return f"⚠️ LARGE POSITION: ${usd_value:,.0f} {coin} - Significant market activity"
        
        elif size_class == PositionSize.MEDIUM:
            return f"📊 MEDIUM POSITION: ${usd_value:,.0f} {coin} - Notable trading activity"
        
        elif size_class == PositionSize.NOTABLE:
            return f"👀 NOTABLE POSITION: ${usd_value:,.0f} {coin} - Worth monitoring"
        
        else:
            return f"📈 Small position: ${usd_value:,.0f} {coin} - Regular trading activity"
    
    def get_classification_stats(self) -> Dict[str, int]:
        """Get statistics on position classifications."""
        stats = {size.value: 0 for size in PositionSize}
        
        # Count classifications from history
        for wallet, history in self.classification_history.items():
            for classification in history:
                if classification in stats:
                    stats[classification] += 1
        
        return stats
    
    def track_classification(self, wallet: str, classification: PositionSize):
        """Track classification for statistics."""
        if wallet not in self.classification_history:
            self.classification_history[wallet] = []
        
        self.classification_history[wallet].append(classification.value)
        
        # Keep only last 100 classifications per wallet
        if len(self.classification_history[wallet]) > 100:
            self.classification_history[wallet] = self.classification_history[wallet][-100:]
