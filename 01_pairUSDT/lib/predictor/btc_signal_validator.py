"""BTC 투자 신호 유효성 검증 모듈.

신호가 투자 결정에 사용되기 전 유효성을 검사한다.

검증 규칙:
1. signal_value: 4가지 값 중 하나여야 함
2. confidence_range: 0.0~1.0 범위 내
3. box_progress_positive: 음수 허용 안 함
4. price_position_range: 0.0~1.0 범위 내 (클리핑 후 체크)
5. reason_nonempty: reason 리스트가 비어있지 않음
6. phase_valid: "BEAR" 또는 "BULL"

주요 함수:
    validate_signal_result — SignalResult 유효성 검증
    ValidationReport       — 검증 결과 보고서
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

log = logging.getLogger(__name__)

VALID_SIGNALS = {"ACCUMULATE", "WATCH", "CAUTION", "EXIT"}
VALID_PHASES = {"BEAR", "BULL"}


@dataclass
class ValidationReport:
    """신호 유효성 검증 결과."""
    is_valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def add_error(self, msg: str) -> None:
        self.errors.append(msg)
        self.is_valid = False

    def add_warning(self, msg: str) -> None:
        self.warnings.append(msg)


def validate_signal_result(signal_result) -> ValidationReport:
    """SignalResult 유효성 검증.

    Args:
        signal_result: btc_investment_signal.SignalResult | None

    Returns:
        ValidationReport
    """
    report = ValidationReport(is_valid=True)

    if signal_result is None:
        report.add_error("signal_result is None")
        return report

    # 1. signal_value
    if signal_result.signal not in VALID_SIGNALS:
        report.add_error(f"invalid signal: '{signal_result.signal}' not in {VALID_SIGNALS}")

    # 2. confidence_range
    conf = signal_result.confidence
    if not (0.0 <= conf <= 1.0):
        report.add_error(f"confidence={conf:.4f} out of [0.0, 1.0]")
    elif conf < 0.3:
        report.add_warning(f"confidence={conf:.4f} is low — signal may be unreliable")
    elif conf > 0.95:
        report.add_warning(f"confidence={conf:.4f} is suspiciously high — review inputs")


    # 3. box_progress_positive
    bp = signal_result.box_progress_ratio
    if bp < 0:
        report.add_error(f"box_progress_ratio={bp:.4f} < 0")
    elif bp > 2.0:
        report.add_warning(f"box_progress_ratio={bp:.4f} > 2.0 (unusual)")

    # 4. price_position_range
    pp = signal_result.price_position
    if not (0.0 <= pp <= 1.0):
        report.add_error(f"price_position={pp:.4f} out of [0.0, 1.0]")

    # 5. reason_nonempty
    if not signal_result.reason:
        report.add_error("reason list is empty")
    elif len(signal_result.reason) > 20:
        report.add_warning(f"reason list has {len(signal_result.reason)} items (unusually long)")

    # 6. phase_valid
    if signal_result.phase not in VALID_PHASES:
        report.add_error(f"invalid phase: '{signal_result.phase}' not in {VALID_PHASES}")

    log.info(
        "[validator] valid=%s errors=%d warnings=%d signal=%s",
        report.is_valid, len(report.errors), len(report.warnings),
        signal_result.signal if signal_result else "None",
    )
    return report
