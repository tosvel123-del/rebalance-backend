from datetime import datetime, timedelta, timezone
from decimal import Decimal
from sqlalchemy import select, delete, and_
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.notification import PendingAlert, Notification, AlertStatus, TradeDirection
from app.models.user import User
from app.services.rebalance_engine import RebalanceAction

class NotificationService:
    SUSTAIN_SECONDS = 600       # 10 minutes
    COOLDOWN_SECONDS = 3600     # 1 hour
    RESOLVE_DELAY_SECONDS = 900 # 15 minutes

    def _now(self) -> datetime:
        return datetime.now(timezone.utc)

    async def _send_fcm_message(self, fcm_token: str | None, title: str, body: str, data: dict) -> str | None:
        if not fcm_token:
            return None
        # FCM integration wrapper (can be mocked or enabled via firebase_admin)
        try:
            from firebase_admin import messaging
            message = messaging.Message(
                notification=messaging.Notification(title=title, body=body),
                data={k: str(v) for k, v in data.items()},
                token=fcm_token,
            )
            response = messaging.send(message)
            return response
        except Exception:
            return "simulated-fcm-msg-id"

    async def _dismiss_fcm_message(self, fcm_token: str | None, fcm_message_id: str | None) -> None:
        if not fcm_token or not fcm_message_id:
            return
        try:
            from firebase_admin import messaging
            # Send data-only message instructing client app to dismiss notification
            message = messaging.Message(
                data={"action": "DISMISS", "fcm_message_id": fcm_message_id},
                token=fcm_token,
            )
            messaging.send(message)
        except Exception:
            pass

    async def is_in_cooldown(self, session: AsyncSession, user_id: int, stock_code: str) -> bool:
        cutoff = self._now() - timedelta(seconds=self.COOLDOWN_SECONDS)
        stmt = select(Notification).where(
            and_(
                Notification.user_id == user_id,
                Notification.stock_code == stock_code,
                Notification.sent_at >= cutoff,
                Notification.status.in_([AlertStatus.ACTIVE, AlertStatus.EXPIRED])
            )
        )
        res = await session.execute(stmt)
        return res.scalar_one_or_none() is not None

    async def process_deviations(self, session: AsyncSession, user_id: int, portfolio_id: int, actions: list[RebalanceAction]) -> None:
        breached_codes = {a.stock_code for a in actions}
        action_map = {a.stock_code: a for a in actions}

        # 1. Fetch current pending alerts for this portfolio
        stmt = select(PendingAlert).where(PendingAlert.portfolio_id == portfolio_id)
        res = await session.execute(stmt)
        current_pendings = res.scalars().all()

        for pending in current_pendings:
            if pending.stock_code not in breached_codes:
                # Deviation resolved before 10 min -> reset/delete pending alert
                await session.delete(pending)
            else:
                # Deviation still breached -> update last_confirmed
                action = action_map[pending.stock_code]
                pending.last_confirmed = self._now()
                pending.current_weight = action.current_weight
                pending.target_weight = action.target_weight
                pending.deviation = action.deviation

        # 2. Add new pending alerts for newly breached codes
        existing_codes = {p.stock_code for p in current_pendings}
        for action in actions:
            if action.stock_code not in existing_codes:
                if not await self.is_in_cooldown(session, user_id, action.stock_code):
                    now = self._now()
                    new_pending = PendingAlert(
                        user_id=user_id,
                        portfolio_id=portfolio_id,
                        stock_code=action.stock_code,
                        first_detected=now,
                        last_confirmed=now,
                        current_weight=action.current_weight,
                        target_weight=action.target_weight,
                        deviation=action.deviation,
                    )
                    session.add(new_pending)

        await session.commit()

    async def promote_matured_pendings(self, session: AsyncSession, user: User, portfolio_id: int, actions: list[RebalanceAction]) -> None:
        action_map = {a.stock_code: a for a in actions}
        cutoff = self._now() - timedelta(seconds=self.SUSTAIN_SECONDS)

        stmt = select(PendingAlert).where(
            and_(
                PendingAlert.portfolio_id == portfolio_id,
                PendingAlert.first_detected <= cutoff
            )
        )
        res = await session.execute(stmt)
        matured_list = res.scalars().all()

        for pending in matured_list:
            action = action_map.get(pending.stock_code)
            if not action:
                await session.delete(pending)
                continue

            # Send FCM notification
            title = f"[{action.direction}] {action.stock_name} 리밸런싱 알림"
            body = f"목표 가중치 대비 편차 {action.deviation * 100:.1f}% 초과. {action.direction} {action.quantity}주 추천"
            data = {
                "portfolio_id": portfolio_id,
                "stock_code": action.stock_code,
                "direction": action.direction,
                "quantity": action.quantity,
            }

            fcm_msg_id = await self._send_fcm_message(user.fcm_token, title, body, data)

            notif = Notification(
                user_id=user.id,
                portfolio_id=portfolio_id,
                stock_code=action.stock_code,
                stock_name=action.stock_name,
                market=action.market,
                direction=TradeDirection(action.direction),
                suggested_qty=action.quantity,
                current_weight=action.current_weight,
                target_weight=action.target_weight,
                deviation=action.deviation,
                price_at_trigger=action.current_price,
                estimated_amount=action.estimated_amount,
                status=AlertStatus.ACTIVE,
                fcm_message_id=fcm_msg_id,
                sent_at=self._now(),
            )
            session.add(notif)
            await session.delete(pending)

        await session.commit()

    async def check_active_alerts(self, session: AsyncSession, portfolio_id: int, actions: list[RebalanceAction]) -> None:
        breached_codes = {a.stock_code for a in actions}

        stmt = select(Notification, User).join(User).where(
            and_(
                Notification.portfolio_id == portfolio_id,
                Notification.status == AlertStatus.ACTIVE
            )
        )
        res = await session.execute(stmt)
        active_pairs = res.all()

        now = self._now()
        resolve_cutoff = now - timedelta(seconds=self.RESOLVE_DELAY_SECONDS)

        for notif, user in active_pairs:
            if notif.stock_code in breached_codes:
                # Still breached -> reset condition_cleared_at
                notif.condition_cleared_at = None
            else:
                # Deviation resolved!
                if notif.condition_cleared_at is None:
                    notif.condition_cleared_at = now
                elif notif.condition_cleared_at <= resolve_cutoff:
                    # Sustained resolution for 15 min -> mark RESOLVED & dismiss FCM
                    notif.status = AlertStatus.RESOLVED
                    notif.resolved_at = now
                    await self._dismiss_fcm_message(user.fcm_token, notif.fcm_message_id)

        await session.commit()

notification_service = NotificationService()
