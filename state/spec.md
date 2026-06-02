# 예측 시스템 사양서
Last Updated: 2026-05-24 | Iteration: 2000 (심화 자율 개발 루프 완료) ✅

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

---

# 🚀 중장기 개선 기획 사양서 (Iteration 101~200) - 무료 지표 개편본

이 섹션은 유료 온체인 지표를 배제하고, 무료 시장 데이터, 공개 블록체인 원천 네트워크 데이터, MLOps 및 아키텍처 개선에 초점을 맞춘 개편안입니다.

## [Part 1] 반감기 및 가격 매크로 (Free Macro & Halving)
* **Iter 101: 복합 반감기 진행률 CMS 모델**
  * 반감기 블록 카운트다운(블록체인 공개 정보)과 현재 박스 카운트를 복합 스코어링(`CMS = 0.6 * box_progress + 0.4 * halving_progress`).
* **Iter 109: 역사적 반감기 기준 국면 전환일 예측 엔진**
  * 과거 반감기 전후 바닥/고점 발생일의 정규분포 데이터를 활용하여 다음 전환 예정 기한 예측.
* **Iter 120: 전고점 대비 최대 낙폭(Drawdown) 분석 모델**
  * 역사적 하락장 바닥 지지력(-80% ~ -85% 낙폭 지점)을 가격 피드에서 실시간 연산하여 lo 경계값 보정에 반영.
* **Iter 129: 메이어 멀티플(Mayer Multiple) 이격 보정기**
  * $MayerMultiple = Price / SMA200(Price)$ 공식을 적용, MM < 0.6(바닥) 및 MM > 2.4(고점) 판정에 활용.
* **Iter 186: 반감기 블록 보상 감축 전후 가격 변동성 피크일 예측 모듈**
  * 보상 감축 전후 60일의 공급 충격 반영 가중치 적용.

## [Part 2] 네트워크 기초체력 및 난이도 (Free Network & Difficulty)
* **Iter 103: 해시레이트 난이도 리본(Difficulty Ribbons) 데드/골든크로스 판독기**
  * 채굴 난이도 이평선(10일~200일) 간의 이격 수축/확장을 분석하여 채굴자 항복(Capitulation) 감지.
* **Iter 161: 해시 리본(Hash Ribbons) 회복 전환 감지기**
  * 공개 해시레이트의 30일 MA가 90일 MA를 돌파할 때의 매수 신뢰도 보정.
* **Iter 162: Difficulty Ribbon Compression 압축도 산출기**
  * 이평선 표준편차 압축 강도를 통한 저점 탐지.
* **Iter 166: 난이도 조정 주기(2,016 블록) 변동성 필터**
  * 난이도 조정 시의 변동폭을 분석하여 네트워크 급변 리스크 감지.
* **Iter 170: 평균 블록 생성 시간 지연 스트레스 분석기**
  * 블록 타겟 타임(10분) 대비 지연 비율을 계산하여 해시파워 이탈 모니터링.

## [Part 3] 다자간 시장 가격 격차 (Free Market Basis & Correlation)
* **Iter 177: CME 선물 프리미엄/디스카운트 괴리 분석기**
  * 시카고상품거래소(CME) 선물 가격과 현물 거래소 가격 격차를 통해 제도권 자금 선호도 분석.
* **Iter 182: 글로벌 M2 통화량(YoY) 매크로 정렬 모듈**
  * 주요국 연간 통화량 변동성 추세와 비트코인 상승 주기 매핑.
* **Iter 183: 달러 인덱스(DXY) 역상관관계 오실레이터**
  * DXY 200일 이평선 이격을 계산하여 위험자산 선호 지수 산출.
* **Iter 184: 미국 국채 10Y-2Y 장단기 금리 역전 해소 모니터**
  * 경기 후퇴 우려 지점을 매크로 매도 경보(`CAUTION`) 타이밍에 연동.
* **Iter 185: 금 대비 비트코인 상대강도(BTC/Gold Ratio) 모멘텀**
  * 안전 자산 대비 상대적 성과 변화 추세 분석.
* **Iter 187: S&P 500 지수 상관관계 Decoupling 필터**
  * 거시 주식 시장과의 90일 피어슨 상관계수를 계산하여 독자적 랠리 여부 분석.

## [Part 4] 데이터 파이프라인 및 백엔드 (Free Architecture & MLOps)
* **Iter 102: Supabase 신호 히스토리(`coin_signal_history`) 스키마 설계**
* **Iter 104: XGBoost 예측 엔진 자동 재학습 파이프라인 기획**
* **Iter 108: FastAPI 응답 속도 향상 인메모리 캐싱(TTL 1시간) 설계**
* **Iter 115: 실시간 데이터 바이낸스 API 동기화 및 정합성 검사 에이전트**
* **Iter 191: 멀티코어 병렬 연산 기반 과거 매크로 백테스팅 엔진**
* **Iter 193: FastAPI 엔드포인트 보안 Rate Limiter(`slowapi`) 설계**
* **Iter 194: ML 모델 가중치 버전 롤백 컨트롤러**
* **Iter 195: 오프라인 캐시 복구 폴백(Fallback) 에이전트**
* **Iter 198: PostgreSQL 연도별 범위 테이블 파티셔닝 설계**
* **Iter 200: GitHub Actions 통합 검증 및 CI/CD 자동화 배포 파이프라인 설계**

## [Part 5] 프론트엔드 및 시각화 (Free Frontend & UI)
* **Iter 105: 텔레그램/디스코드 웹훅 알림 라우터**
* **Iter 112: XGBoost 예측 변수 기여도 SHAP 설명 패널 UI**
* **Iter 113: 개인별 투자성향(보수/중립/공격) 동적 비중 계산기 UI**
* **Iter 116: 샌드박스(Sandbox) 가상 수익률 백테스트 시뮬레이션 UI**
* **Iter 192: Supabase Realtime CDC Websocket 브로드캐스트 연동**
* **Iter 196: React 기반 SHAP force plot 대화형 시각화 게이지 차트**
* **Iter 199: 모바일 뷰포트 대응 CSS flex grid 및 터치 타겟(48px) 최적화 UI**
