# predict.py 기능별 분할 계획서

## [도메인 판단]
- **금융/Crypto**: 소수점 오차 방지 규칙 적용 가능. 단, 기존 ML 파이프라인(numpy/pandas)은 float 기반이므로 Decimal 전환은 별도 작업으로 분리.

## [기능 목록 및 파일 분할]

| 모듈 | 기능 | 함수 목록 |
|------|------|-----------|
| `predict_schema.py` | SQL 상수 | INSERT_SQL, CREATE_PATHS_SQL, CREATE_PEAKS_SQL |
| `predict_btc_anchor.py` | BTC 앵커 계산 | calc_btc_anchor |
| `predict_features.py` | 피처 벡터 | build_feature_vector |
| `predict_bottom.py` | Bottom 예측 | calc_bottom_btc, calc_bottom_alt |
| `predict_peak.py` | Peak 예측 | compute_cross_coin_peak_ratio, calc_peak_btc, calc_peak_alt, calc_peak_hybrid_for_coin |
| `predict_judge.py` | BULL/BEAR 판정 | check_lower_low_slope, check_force_bear, judge_bull_bear |
| `predict_box_bull.py` | Bull 시나리오 | build_bull_path_rows, make_bull_row, build_bull_scenario, build_bull_chain |
| `predict_box_bear.py` | Bear 시나리오 | build_bear_scenario, build_bear_chain, build_bear_box_day_points 등 |
| `predict_model.py` | 모델 예측/유사도 | find_most_similar_pattern, get_model_predictions |
| `predict_paths.py` | 경로 보간/재구성 | interpolate_segment, build_paths_for_cycle, rebuild_prediction_paths |
| `predict.py` | 진입점(파사드) | predict_and_insert, print_prediction_summary, 내부 오케스트레이션 |

## [대상 파일]
- `pairUSDT/lib/predictor/predict.py` (1925줄) → 11개 모듈로 분할

## [예상 위험]
1. 순환 import: 모듈 간 의존성 그래프가 DAG를 유지해야 함
2. 기존 032_train_and_predict_box.py 호출 호환성
3. 테스트 없이 리팩터 시 회귀 버그

## [검증 기준]
1. `032_train_and_predict_box.py` 실행 성공 (기존 플로우 동일)
2. `predict_and_insert`, `print_prediction_summary` import 정상
3. CREATE_PATHS_SQL, CREATE_PEAKS_SQL import 정상
4. 단위 테스트 10개 이상 통과
5. Linter 에러 0개

## [완료 조건]
- 테스트 10개 전원 통과
- 에러(빨간 줄) 0개
- 032_train_and_predict_box.py 정상 실행
