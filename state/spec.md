# 예측 시스템 사양서
Last Updated: 2026-05-21 | Iteration: 100 (완료) ✅

## 프로젝트 핵심 목표

**대상 코인**: BTC
**목표**: 사이클 내 Bear/Bull 세부 박스권 분석 후, 현재 사이클 위치를 파악하여 투자 타이밍 신호 생성

### 투자 신호 4단계
| 신호 | 설명 | 조건 |
|---|---|---|
| `ACCUMULATE` | 적극 매수 — Bear 사이클 후반, 저점 근처 | 박스 진행률 > 60%, lo 근처 |
| `WATCH` | 관망 — 방향 불확실 | 박스 중반, 방향 미결 |
| `CAUTION` | 주의 — Bull 후반, 고점 근처 | Bull 박스 진행률 > 60%, hi 근처 |
| `EXIT` | 매도 준비 — 사이클 피크 임박 | peak_day 임박, 고점 예측 |

### Bear 사이클 4단계 분류
| Stage | 범위 | 액션 |
|---|---|---|
| Stage 1 | 0~30% | 대기 |
| Stage 2 | 30~60% | 소규모 분할 매수 |
| Stage 3 | 60~85% | 적극 분할 매수 |
| Stage 4 | 85%+ | 최대 비중 진입 |

### Bull 사이클 4단계 분류
| Stage | 범위 | 액션 |
|---|---|---|
| Stage 1 | 0~25% | 포지션 유지 |
| Stage 2 | 25~55% | 일부 수익 실현 |
| Stage 3 | 55~80% | 비중 축소 |
| Stage 4 | 80%+ | 매도 준비 |

---

## 완료된 모듈 (Iter 9~30)

### 핵심 투자 신호 모듈 (P1)
| 파일 | 역할 |
|---|---|
| `lib/predictor/btc_cycle_position.py` | Bear/Bull 박스 진행률·가격 위치·목표가 거리 계산 |
| `lib/predictor/btc_investment_signal.py` | ACCUMULATE/WATCH/CAUTION/EXIT 4단계 신호 생성 |
| `lib/predictor/btc_signal_adapter.py` | DataFrame → CyclePosition 자동 변환 |
| `lib/predictor/predict_judge.py` | judge_btc_with_signal 추가 (기존 9-tuple + SignalResult) |
| `lib/predictor/btc_signal_payload.py` | SignalResult → API payload 직렬화 |
| `lib/predictor/btc_signal_descriptor.py` | Bear/Bull 통합 라우팅 설명 생성기 |
| `lib/predictor/btc_signal_api.py` | **단일 공개 진입점** — 전체 파이프라인 |

### 설명 및 메시지 모듈
| 파일 | 역할 |
|---|---|
| `lib/predictor/bear_stage_descriptor.py` | Bear 4단계 + 한국어/영어 메시지 |
| `lib/predictor/bull_stage_descriptor.py` | Bull 4단계 + 한국어/영어 메시지 |
| `lib/predictor/btc_signal_history.py` | 신호 히스토리 추적 (연속 카운트, 변화 감지) |
| `lib/predictor/btc_signal_confidence_scorer.py` | 히스토리+위치 기반 신뢰도 보정 |
| `lib/predictor/btc_signal_validator.py` | SignalResult 유효성 검증 |


## 신규 모듈 (Iter 31~100)
| 파일 | 역할 |
|---|---|
| `lib/predictor/btc_cycle_position.py` | `to_dict()` 직렬화 메서드 추가 |
| `lib/predictor/btc_signal_history.py` | `get_scorer_params()` 헬퍼 추가 |
| `lib/predictor/btc_signal_validator.py` | `confidence` 저/고 경고 확장 |
| `lib/predictor/btc_signal_api.py` | `get_signal_summary()` 단일 요약 함수 추가 |
| `lib/predictor/btc_signal_adapter.py` | `to_position_summary()` UI 요약 함수 추가 |
| `lib/predictor/bear_stage_descriptor.py` | `format_stage_label()` UI 레이블 함수 추가 |
| `lib/predictor/bull_stage_descriptor.py` | `format_stage_label()` UI 레이블 함수 추가 |

---

## 최종 테스트 현황
- **전체 테스트 수**: **596개** (Iter 30 367개 → 229개 신규 추가)
- **전체 PASS**: ✅ 596/596
- **테스트 대표 범주**:
  - 신호 파이프라인 통합 (pipeline + payload 일관성): 11개
  - scorer 파라미터 조합 + validator 통합: 10개
  - 신호 히스토리 관리 + 루프 시뮬레이션: 14개
  - 경계값 / 엣지케이스 / 시나리오: 42개
  - 시스템 smoke test + docstring: 12개
  - 관련 모듈 업그레이드 (어댑터, 페이로드, 디스크립터, 패턴매캘): 140개

---

## 사용 예시 (Iteration 100 기준)

```python
from lib.predictor.btc_signal_api import btc_investment_pipeline, get_signal_summary
from lib.predictor.btc_signal_history import SignalHistory, SignalHistoryEntry

history = SignalHistory(max_size=100)

# 매 실행 시 히스토리에서 scorer 파라미터 획득
params = history.get_scorer_params()
result = btc_investment_pipeline(
    df=coin_analysis_df,
    cycle_number=5, phase="BEAR",
    current_price_pct=20.0,
    box_lo=18.0, box_hi=35.0,
    target_price_pct=17.0,
    **params,  # consecutive_count + is_signal_changed
)

print(result["signal"]["signal"])          # "ACCUMULATE"
print(result["description"]["message_ko"]) # "Bear 후반입니다..."
print(result["validation"]["is_valid"])    # True
print(get_signal_summary(result))          # "[BEAR cy=5] ACCUMULATE (conf=0.84) - ..."

# 히스토리에 기록
history.append(SignalHistoryEntry(
    signal=result["signal"]["signal"],
    phase="BEAR", confidence=result["signal"]["confidence"],
    stage=result["description"]["stage"],
    cycle_number=5, box_progress_ratio=0.7,
))
```

---

## 다음 단계 (백로그)
- [ ] 백엔드 FastAPI 라우터 `/btc/signal` 엔드포인트 연결
- [ ] Supabase에 신호 히스토리 저장 기능
- [ ] 프론트엔드 투자 신호 카드 컴포넌트 연동
- [ ] 실제 BTC 시세 데이터 기반 신호 검증 (실전 테스트)

