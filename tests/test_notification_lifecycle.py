from datetime import datetime, timedelta, timezone
from decimal import Decimal
import pytest
from app.models.notification import PendingAlert, Notification, AlertStatus, TradeDirection
from app.models.user import User
from app.services.rebalance_engine import RebalanceAction
from app.services.notification_service import NotificationService

@pytest.fixture
def notif_service():
    return NotificationService()

def test_sustain_and_resolve_constants(notif_service):
    assert notif_service.SUSTAIN_SECONDS == 600       # 10분
    assert notif_service.COOLDOWN_SECONDS == 3600     # 1시간
    assert notif_service.RESOLVE_DELAY_SECONDS == 900 # 15분
