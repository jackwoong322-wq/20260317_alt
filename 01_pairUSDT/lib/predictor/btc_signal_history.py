"""BTC 투자 신호 히스토리 추적 모듈.

생성된 투자 신호의 히스토리를 메모리 내에 추적하고,
신호 변화(Signal Change) 감지 및 연속 같은 신호 카운트를 제공한다.

주요 클래스:
    SignalHistoryEntry — 개별 히스토리 항목
    SignalHistory      — 히스토리 관리자

주요 기능:
    - 신호 추가 (append)
    - 최근 N개 신호 조회
    - 신호 변화 감지 (is_signal_changed)
    - 연속 같은 신호 카운트 (consecutive_count)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone

log = logging.getLogger(__name__)


@dataclass
class SignalHistoryEntry:
    """개별 신호 히스토리 항목."""
    signal: str          # ACCUMULATE | WATCH | CAUTION | EXIT
    phase: str           # BEAR | BULL
    confidence: float
    stage: int
    cycle_number: int
    box_progress_ratio: float
    timestamp: str = field(default_factory=lambda: datetime.now(tz=timezone.utc).isoformat())


class SignalHistory:
    """BTC 투자 신호 히스토리 관리자.

    메모리 내 최대 N개의 신호를 유지한다.
    """

    def __init__(self, max_size: int = 100):
        if max_size < 1:
            raise ValueError("max_size는 1 이상이어야 합니다.")
        self._max_size = max_size
        self._entries: list[SignalHistoryEntry] = []

    def append(self, entry: SignalHistoryEntry) -> None:
        """새 신호 추가. max_size 초과 시 가장 오래된 항목 제거."""
        self._entries.append(entry)
        if len(self._entries) > self._max_size:
            self._entries.pop(0)
        log.debug(
            "[signal_history] 추가: signal=%s phase=%s cy=%d (total=%d)",
            entry.signal, entry.phase, entry.cycle_number, len(self._entries),
        )

    def latest(self) -> SignalHistoryEntry | None:
        """가장 최근 신호 반환. 비어있으면 None."""
        return self._entries[-1] if self._entries else None

    def recent(self, n: int = 5) -> list[SignalHistoryEntry]:
        """최근 n개 신호 반환 (최신순)."""
        return list(reversed(self._entries[-n:]))

    def is_signal_changed(self) -> bool:
        """최근 두 신호가 다른지 여부.

        Returns:
            True: 신호가 바뀜
            False: 같음 또는 데이터 부족
        """
        if len(self._entries) < 2:
            return False
        return self._entries[-1].signal != self._entries[-2].signal

    def consecutive_count(self) -> int:
        """현재 신호가 연속으로 몇 번 이어졌는지 카운트.

        Returns:
            1 이상. 단일 항목이면 1.
        """
        if not self._entries:
            return 0
        latest_signal = self._entries[-1].signal
        count = 0
        for entry in reversed(self._entries):
            if entry.signal == latest_signal:
                count += 1
            else:
                break
        return count

    def signal_distribution(self) -> dict[str, int]:
        """전체 히스토리에서 각 신호의 횟수 반환."""
        dist: dict[str, int] = {}
        for entry in self._entries:
            dist[entry.signal] = dist.get(entry.signal, 0) + 1
        return dist

    def clear(self) -> None:
        """히스토리 전체 초기화."""
        self._entries.clear()

    def __len__(self) -> int:
        return len(self._entries)

    def get_scorer_params(self) -> dict:
        """btc_investment_pipeline/generate_btc_signal에 전달할 scorer 파라미터 반환.

        Returns:
            {
                "consecutive_count": int,   # 연속 같은 신호 횟수 (최소 1)
                "is_signal_changed": bool,  # 직전 신호에서 변화 여부
            }
        """
        count = self.consecutive_count()
        changed = self.is_signal_changed()
        return {
            "consecutive_count": max(1, count),
            "is_signal_changed": changed,
        }

