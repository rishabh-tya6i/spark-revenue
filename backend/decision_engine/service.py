import logging
import json
from datetime import datetime
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from fastapi import APIRouter, HTTPException

from ..db import DecisionRecord, AlertRecord, NewsSentiment, OptionSignal, SessionLocal
from ..config import settings
from .schemas import FusedDecisionOut, DecisionRequest, DecisionResponse
from . import fusion

logger = logging.getLogger(__name__)

class DecisionEngineService:
    def __init__(self, session_factory=SessionLocal):
        self.session_factory = session_factory

    def collect_inputs(self, symbol: str, interval: str) -> Dict[str, Any]:
        """
        Fetches underlying inputs from DB/Services.
        In v1, we focus on Sentiment and Options which are already in DB.
        Price and RL can be added later or stubbed here.
        """
        with self.session_factory() as session:
            # 1. Sentiment: Last 10 items
            recent_sentiments = session.query(NewsSentiment).order_by(
                NewsSentiment.timestamp.desc()
            ).limit(10).all()
            
            # 2. Options: Latest signal
            latest_options = session.query(OptionSignal).filter(
                OptionSignal.symbol == symbol
            ).order_by(OptionSignal.timestamp.desc()).first()
            
            # 3. Price/RL: Stubs for v1 integration
            # These would ideally call PricePredictionService.predict and RLService.act
            price_data = {"label": "NEUTRAL", "probabilities": {"NEUTRAL": 1.0}}
            rl_data = {"action": "HOLD", "confidence": 1.0}

            return {
                "sentiment": recent_sentiments,
                "options": latest_options,
                "price": price_data,
                "rl": rl_data
            }

    def compute_and_store_decision(self, symbol: str, interval: str) -> FusedDecisionOut:
        inputs = self.collect_inputs(symbol, interval)
        
        # Normalize
        price_dir, price_conf = fusion.normalize_price_signal(
            inputs["price"]["label"], inputs["price"]["probabilities"]
        )
        rl_act, rl_conf = fusion.normalize_rl_signal(
            inputs["rl"]["action"], inputs["rl"]["confidence"]
        )
        sent_scores = [s.sentiment_score for s in inputs["sentiment"]]
        sent_labels = [s.sentiment_label for s in inputs["sentiment"]]
        sent_avg, sent_maj = fusion.normalize_sentiment(sent_scores, sent_labels)
        
        opt = inputs["options"]
        opt_lab, opt_pcr, opt_pain = fusion.normalize_options_signal(
            opt.signal_label if opt else None,
            opt.pcr if opt else None,
            opt.max_pain_strike if opt else None
        )
        
        # Fuse
        label, score = fusion.fuse_signals(
            price_dir, price_conf, rl_act, rl_conf, sent_avg, opt_lab, opt_pcr
        )
        
        # Store
        with self.session_factory() as session:
            record = DecisionRecord(
                symbol=symbol,
                interval=interval,
                timestamp=datetime.utcnow(),
                decision_label=label,
                decision_score=score,
                price_direction=price_dir,
                price_confidence=price_conf,
                rl_action=rl_act,
                rl_confidence=rl_conf,
                sentiment_score=sent_avg,
                sentiment_label=sent_maj,
                options_signal_label=opt_lab,
                options_pcr=opt_pcr,
                options_max_pain_strike=opt_pain
            )
            session.add(record)
            session.commit()
            session.refresh(record)
            return FusedDecisionOut.model_validate(record)

    def generate_alert_from_decision(self, decision_out: FusedDecisionOut) -> Optional[AlertRecord]:
        if decision_out.decision_score >= settings.DECISION_MIN_CONFIDENCE:
            alert_type = f"HIGH_CONFIDENCE_{decision_out.decision_label}"
            importance = decision_out.decision_score
            message = f"High confidence {decision_out.decision_label} signal for {decision_out.symbol} ({decision_out.interval})"
            
            with self.session_factory() as session:
                alert = AlertRecord(
                    symbol=decision_out.symbol,
                    interval=decision_out.interval,
                    timestamp=datetime.utcnow(),
                    alert_type=alert_type,
                    message=message,
                    importance=importance,
                    delivered_channels="desktop"
                )
                session.add(alert)
                session.commit()
                session.refresh(alert)
                return alert
        return None

    def get_latest_decision(self, symbol: str, interval: str) -> Optional[FusedDecisionOut]:
        with self.session_factory() as session:
            result = session.query(DecisionRecord).filter(
                DecisionRecord.symbol == symbol,
                DecisionRecord.interval == interval
            ).order_by(DecisionRecord.timestamp.desc()).first()
            if result:
                return FusedDecisionOut.model_validate(result)
        return None

    def get_recent_alerts(self, limit: int = 20) -> List[AlertRecord]:
        with self.session_factory() as session:
            return session.query(AlertRecord).order_by(AlertRecord.timestamp.desc()).limit(limit).all()

# Router
router = APIRouter()

@router.post("/decision/compute", response_model=DecisionResponse)
async def compute_decision(request: DecisionRequest):
    service = DecisionEngineService()
    decision = service.compute_and_store_decision(request.symbol, request.interval)
    alert_record = service.generate_alert_from_decision(decision)
    
    alert_json = None
    if alert_record:
        alert_json = {
            "alert_type": alert_record.alert_type,
            "message": alert_record.message,
            "importance": alert_record.importance
        }
        
    return DecisionResponse(decision=decision, alert=alert_json)

@router.get("/decision/latest", response_model=FusedDecisionOut)
async def get_latest_decision(symbol: str, interval: str = "5m"):
    service = DecisionEngineService()
    decision = service.get_latest_decision(symbol, interval)
    if not decision:
        raise HTTPException(status_code=404, detail="No decision found")
    return decision

@router.get("/alerts/recent")
async def get_recent_alerts(limit: int = 20):
    service = DecisionEngineService()
    alerts = service.get_recent_alerts(limit)
    return alerts
