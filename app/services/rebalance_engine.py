import math
from dataclasses import dataclass
from decimal import Decimal
from typing import Literal
from app.models.portfolio import Portfolio, Holding, TargetWeight

@dataclass
class RebalanceAction:
    stock_code: str
    stock_name: str
    market: str
    direction: Literal["BUY", "SELL"]
    quantity: int
    current_weight: Decimal
    target_weight: Decimal
    deviation: Decimal
    estimated_amount: Decimal
    current_price: Decimal

class RebalanceEngine:
    def calculate_total_value(self, portfolio: Portfolio, prices: dict[str, Decimal]) -> Decimal:
        stock_value = sum(
            prices.get(h.stock_code, Decimal("0")) * Decimal(h.quantity)
            for h in portfolio.holdings
        )
        return Decimal(portfolio.cash_balance) + stock_value

    def check_portfolio(self, portfolio: Portfolio, prices: dict[str, Decimal]) -> list[RebalanceAction]:
        total_value = self.calculate_total_value(portfolio, prices)
        if total_value <= 0:
            return []

        target_map: dict[str, TargetWeight] = {tw.stock_code: tw for tw in portfolio.target_weights}
        threshold_decimal = Decimal(portfolio.threshold_pct) / Decimal("100")
        actions: list[RebalanceAction] = []

        for holding in portfolio.holdings:
            code = holding.stock_code
            price = prices.get(code)
            if price is None or price <= 0:
                continue

            target_item = target_map.get(code)
            target_pct = Decimal(target_item.target_weight_pct) if target_item else Decimal("0")
            w_target = target_pct / Decimal("100")

            holding_val = price * Decimal(holding.quantity)
            w_curr = holding_val / total_value
            deviation = abs(w_curr - w_target)

            if deviation > threshold_decimal:
                raw_diff = (total_value * w_target) - holding_val
                delta_q_raw = raw_diff / price

                if delta_q_raw > 0:
                    delta_q = math.floor(delta_q_raw)
                    direction = "BUY"
                else:
                    delta_q = math.ceil(delta_q_raw)
                    direction = "SELL"

                if delta_q == 0:
                    continue

                abs_qty = abs(delta_q)
                actions.append(RebalanceAction(
                    stock_code=code,
                    stock_name=holding.stock_name,
                    market=holding.market,
                    direction=direction,
                    quantity=abs_qty,
                    current_weight=round(w_curr, 4),
                    target_weight=round(w_target, 4),
                    deviation=round(deviation, 4),
                    estimated_amount=round(price * Decimal(abs_qty), 2),
                    current_price=price,
                ))

        return actions
