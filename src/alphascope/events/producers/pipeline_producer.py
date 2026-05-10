from __future__ import annotations

from alphascope.events.event_bus import EventBus
from alphascope.events.event_types import (
    FEATURES_COMPUTED,
    MARKET_DATA_UPDATED,
    MODEL_PREDICTION_READY,
    PORTFOLIO_UPDATED,
    RANKING_UPDATED,
    TRADE_EXECUTED,
    Event,
)


class PipelineEventProducer:
    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus

    def market_data_updated(self, payload: dict) -> Event:
        return self.event_bus.publish(Event(MARKET_DATA_UPDATED, payload))

    def features_computed(self, payload: dict) -> Event:
        return self.event_bus.publish(Event(FEATURES_COMPUTED, payload))

    def model_prediction_ready(self, payload: dict) -> Event:
        return self.event_bus.publish(Event(MODEL_PREDICTION_READY, payload))

    def ranking_updated(self, payload: dict) -> Event:
        return self.event_bus.publish(Event(RANKING_UPDATED, payload))

    def trade_executed(self, payload: dict) -> Event:
        return self.event_bus.publish(Event(TRADE_EXECUTED, payload))

    def portfolio_updated(self, payload: dict) -> Event:
        return self.event_bus.publish(Event(PORTFOLIO_UPDATED, payload))
