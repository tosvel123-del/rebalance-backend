from decimal import Decimal
import pytest
from app.models.portfolio import Portfolio, Holding, TargetWeight
from app.services.rebalance_engine import RebalanceEngine

@pytest.fixture
def engine():
    return RebalanceEngine()

@pytest.fixture
def sample_portfolio():
    p = Portfolio(
        id=1,
        user_id=1,
        name="Test Portfolio",
        cash_balance=Decimal("1000000"),
        threshold_pct=Decimal("3.00"),
    )
    # Holdings: 삼성전자 10주, SK하이닉스 5주
    h1 = Holding(portfolio_id=1, stock_code="005930", stock_name="삼성전자", quantity=10, market="KR")
    h2 = Holding(portfolio_id=1, stock_code="000660", stock_name="SK하이닉스", quantity=5, market="KR")
    p.holdings = [h1, h2]

    # Target Weights: 삼성전자 50%, SK하이닉스 30% (현금 20%)
    t1 = TargetWeight(portfolio_id=1, stock_code="005930", target_weight_pct=Decimal("50.00"), market="KR")
    t2 = TargetWeight(portfolio_id=1, stock_code="000660", target_weight_pct=Decimal("30.00"), market="KR")
    p.target_weights = [t1, t2]

    return p

def test_no_action_when_within_threshold(engine, sample_portfolio):
    # 총 자산: 1,000,000(현금) + 70,000*10(삼성전자) + 140,000*5(SK하이닉스) = 2,400,000
    # 삼성전자 현재 비중: 700,000 / 2,400,000 = 29.17% (목표 50%, 편차 20.83% -> 초과!)
    # 이번 케이스에서는 편차가 3% 이내가 되도록 가격 조정
    # 삼성전자 50%: 1,200,000원치 -> 120,000원 * 10주
    # SK하이닉스 30%: 720,000원치 -> 144,000원 * 5주
    # 총 자산: 1,000,000 + 1,200,000 + 720,000 = 2,920,000
    # 삼성 비중: 1200000 / 2920000 = 41.1% -> 50% 대비 편차 8.9%
    
    # 완전히 동일한 비중 가격 설정
    # 총 자산 = 1,000,000(현금) / (1 - 0.5 - 0.3) = 5,000,000
    # 삼성전자: 2,500,000원 / 10주 = 250,000원 (50%)
    # SK하이닉스: 1,500,000원 / 5주 = 300,000원 (30%)
    prices = {
        "005930": Decimal("250000"),
        "000660": Decimal("300000"),
    }

    actions = engine.check_portfolio(sample_portfolio, prices)
    assert len(actions) == 0

def test_buy_and_sell_actions(engine, sample_portfolio):
    # 삼성전자 주가 대폭 하락 (매수 조건)
    # SK하이닉스 주가 대폭 상승 (매도 조건)
    prices = {
        "005930": Decimal("50000"),   # 10주 = 500,000원
        "000660": Decimal("400000"),  # 5주 = 2,000,000원
    }
    # 현금 = 1,000,000
    # 총 자산 = 1,000,000 + 500,000 + 2,000,000 = 3,500,000
    # 삼성 현재 비중 = 500,000 / 3,500,000 = 14.29% (목표 50%, 편차 35.71% > 3%)
    # SK하이닉스 현재 비중 = 2,000,000 / 3,500,000 = 57.14% (목표 30%, 편차 27.14% > 3%)

    actions = engine.check_portfolio(sample_portfolio, prices)
    assert len(actions) == 2

    action_map = {a.stock_code: a for a in actions}
    
    # 삼성전자 BUY 수량: floor((3,500,000 * 0.5 - 500,000) / 50,000) = floor(1,250,000 / 50,000) = 25주
    assert action_map["005930"].direction == "BUY"
    assert action_map["005930"].quantity == 25

    # SK하이닉스 SELL 수량: ceil((3,500,000 * 0.3 - 2,000,000) / 400,000) = ceil(-950,000 / 400,000) = -2주 -> 2주 매도
    assert action_map["000660"].direction == "SELL"
    assert action_map["000660"].quantity == 2
