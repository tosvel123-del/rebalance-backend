import unittest
from decimal import Decimal
import sys
import os

# Add backend directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.models.portfolio import Portfolio, Holding, TargetWeight
from app.services.rebalance_engine import RebalanceEngine
from app.services.notification_service import NotificationService
from app.services.price_service import price_service, StockReference

class TestRebalanceEngine(unittest.TestCase):
    def setUp(self):
        self.engine = RebalanceEngine()
        self.portfolio = Portfolio(
            id=1,
            user_id=1,
            name="Test Portfolio",
            cash_balance=Decimal("1000000"),
            threshold_pct=Decimal("3.00"),
        )
        h1 = Holding(portfolio_id=1, stock_code="005930", stock_name="삼성전자", quantity=10, market="KR")
        h2 = Holding(portfolio_id=1, stock_code="000660", stock_name="SK하이닉스", quantity=5, market="KR")
        self.portfolio.holdings = [h1, h2]

        t1 = TargetWeight(portfolio_id=1, stock_code="005930", target_weight_pct=Decimal("50.00"), market="KR")
        t2 = TargetWeight(portfolio_id=1, stock_code="000660", target_weight_pct=Decimal("30.00"), market="KR")
        self.portfolio.target_weights = [t1, t2]

    def test_no_action_when_within_threshold(self):
        prices = {
            "005930": Decimal("250000"),
            "000660": Decimal("300000"),
        }
        actions = self.engine.check_portfolio(self.portfolio, prices)
        self.assertEqual(len(actions), 0)

    def test_buy_and_sell_actions(self):
        prices = {
            "005930": Decimal("50000"),
            "000660": Decimal("400000"),
        }
        actions = self.engine.check_portfolio(self.portfolio, prices)
        self.assertEqual(len(actions), 2)

        action_map = {a.stock_code: a for a in actions}
        self.assertEqual(action_map["005930"].direction, "BUY")
        self.assertEqual(action_map["005930"].quantity, 25)

        self.assertEqual(action_map["000660"].direction, "SELL")
        self.assertEqual(action_map["000660"].quantity, 2)

    def test_market_classification(self):
        self.assertEqual(
            price_service._provider_for(StockReference(code="005930", market="US")).source_name,
            "naver_finance",
        )

    def test_notification_constants(self):
        service = NotificationService()
        self.assertEqual(service.SUSTAIN_SECONDS, 600)      # 10 min
        self.assertEqual(service.COOLDOWN_SECONDS, 3600)    # 1 hour
        self.assertEqual(service.RESOLVE_DELAY_SECONDS, 900)# 15 min

if __name__ == "__main__":
    unittest.main()
