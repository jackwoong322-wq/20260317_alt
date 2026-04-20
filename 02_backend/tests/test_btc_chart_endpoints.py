import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from main import app


FIXTURE_TABLES = {
    "ohlcv": [
        {
            "coin_id": "bitcoin",
            "date": "2026-04-18",
            "open": 70000,
            "high": 71000,
            "low": 69000,
            "close": 70500,
            "volume_quote": 123456.7,
        },
        {
            "coin_id": "bitcoin",
            "date": "2026-04-19",
            "open": 70500,
            "high": 72000,
            "low": 70000,
            "close": 71500,
            "volume_quote": 765432.1,
        },
    ],
    "alt_cycle_data": [
        {
            "coin_id": "bitcoin",
            "cycle_number": 1,
            "cycle_name": "Cycle 2011",
            "days_since_peak": 0,
            "close_rate": 100.0,
            "peak_date": "2011-06-08",
            "timestamp": "2011-06-08T00:00:00",
        },
        {
            "coin_id": "bitcoin",
            "cycle_number": 1,
            "cycle_name": "Cycle 2011",
            "days_since_peak": 1,
            "close_rate": 92.76,
            "peak_date": "2011-06-08",
            "timestamp": "2011-06-09T00:00:00",
        },
        {
            "coin_id": "bitcoin",
            "cycle_number": 2,
            "cycle_name": "Cycle 2013",
            "days_since_peak": 0,
            "close_rate": 100.0,
            "peak_date": "2013-11-29",
            "timestamp": "2013-11-29T00:00:00",
        },
        {
            "coin_id": "bitcoin",
            "cycle_number": 2,
            "cycle_name": "Cycle 2013",
            "days_since_peak": 2,
            "close_rate": 88.0,
            "peak_date": "2013-11-29",
            "timestamp": "2013-12-01T00:00:00",
        },
        {
            "coin_id": "bitcoin",
            "cycle_number": 3,
            "cycle_name": "Cycle 2017",
            "days_since_peak": 0,
            "close_rate": 100.0,
            "peak_date": "2017-12-17",
            "timestamp": "2017-12-17T00:00:00",
        },
        {
            "coin_id": "bitcoin",
            "cycle_number": 3,
            "cycle_name": "Cycle 2017",
            "days_since_peak": 1,
            "close_rate": 85.5,
            "peak_date": "2017-12-17",
            "timestamp": "2017-12-18T00:00:00",
        },
        {
            "coin_id": "bitcoin",
            "cycle_number": 4,
            "cycle_name": "Cycle 2021",
            "days_since_peak": 0,
            "close_rate": 100.0,
            "peak_date": "2021-11-10",
            "timestamp": "2021-11-10T00:00:00",
        },
        {
            "coin_id": "bitcoin",
            "cycle_number": 4,
            "cycle_name": "Cycle 2021",
            "days_since_peak": 1,
            "close_rate": 97.5,
            "peak_date": "2021-11-10",
            "timestamp": "2021-11-11T00:00:00",
        },
        {
            "coin_id": "bitcoin",
            "cycle_number": 4,
            "cycle_name": "Cycle 2021",
            "days_since_peak": 399,
            "close_rate": 26.65,
            "peak_date": "2021-11-10",
            "timestamp": "2022-12-14T00:00:00",
        },
        {
            "coin_id": "bitcoin",
            "cycle_number": 4,
            "cycle_name": "Cycle 2021",
            "days_since_peak": 404,
            "close_rate": 23.56,
            "peak_date": "2021-11-10",
            "timestamp": "2022-12-19T00:00:00",
        },
        {
            "coin_id": "bitcoin",
            "cycle_number": 4,
            "cycle_name": "Cycle 2021",
            "days_since_peak": 430,
            "close_rate": 35.12,
            "peak_date": "2021-11-10",
            "timestamp": "2023-01-14T00:00:00",
        },
        {
            "coin_id": "bitcoin",
            "cycle_number": 5,
            "cycle_name": "Current Cycle (2025)",
            "days_since_peak": 0,
            "close_rate": 100.0,
            "peak_date": "2025-10-06",
            "timestamp": "2025-10-06T00:00:00",
        },
        {
            "coin_id": "bitcoin",
            "cycle_number": 5,
            "cycle_name": "Current Cycle (2025)",
            "days_since_peak": 2,
            "close_rate": 96.4,
            "peak_date": "2025-10-06",
            "timestamp": "2025-10-08T00:00:00",
        },
        {
            "coin_id": "bitcoin",
            "cycle_number": 5,
            "cycle_name": "Current Cycle (2025)",
            "days_since_peak": 4,
            "close_rate": 88.8,
            "peak_date": "2025-10-06",
            "timestamp": "2025-10-10T00:00:00",
        },
        {
            "coin_id": "bitcoin",
            "cycle_number": 5,
            "cycle_name": "Current Cycle (2025)",
            "days_since_peak": 5,
            "close_rate": 80.1,
            "peak_date": "2025-10-06",
            "timestamp": "2025-10-11T00:00:00",
        },
        {
            "coin_id": "bitcoin",
            "cycle_number": 5,
            "cycle_name": "Current Cycle (2025)",
            "days_since_peak": 7,
            "close_rate": 78.2,
            "peak_date": "2025-10-06",
            "timestamp": "2025-10-13T00:00:00",
        },
    ],
    "coin_analysis_results": [
        {"coin_id": "bitcoin", "cycle_number": 1, "phase": "BEAR", "is_completed": 1, "is_prediction": 0, "box_index": 1, "start_x": 0, "end_x": 1, "hi": 100.0, "lo": 92.76, "hi_day": 0, "lo_day": 1},
        {"coin_id": "bitcoin", "cycle_number": 1, "phase": "BULL", "is_completed": 1, "is_prediction": 0, "box_index": 1, "start_x": 10, "end_x": 20, "hi": 90.0, "lo": 80.0, "hi_day": 10, "lo_day": 15},
        {"coin_id": "bitcoin", "cycle_number": 2, "phase": "BEAR", "is_completed": 1, "is_prediction": 0, "box_index": 1, "start_x": 0, "end_x": 2, "hi": 100.0, "lo": 88.0, "hi_day": 0, "lo_day": 2},
        {"coin_id": "bitcoin", "cycle_number": 2, "phase": "BULL", "is_completed": 1, "is_prediction": 0, "box_index": 1, "start_x": 20, "end_x": 30, "hi": 85.0, "lo": 70.0, "hi_day": 20, "lo_day": 25},
        {"coin_id": "bitcoin", "cycle_number": 3, "phase": "BEAR", "is_completed": 1, "is_prediction": 0, "box_index": 1, "start_x": 0, "end_x": 1, "hi": 100.0, "lo": 85.5, "hi_day": 0, "lo_day": 1},
        {"coin_id": "bitcoin", "cycle_number": 3, "phase": "BULL", "is_completed": 1, "is_prediction": 0, "box_index": 1, "start_x": 15, "end_x": 25, "hi": 82.0, "lo": 60.0, "hi_day": 15, "lo_day": 20},
        {"coin_id": "bitcoin", "cycle_number": 4, "phase": "BEAR", "is_completed": 1, "is_prediction": 0, "box_index": 1, "start_x": 5, "end_x": 11, "hi": 95.0, "lo": 82.0, "hi_day": 6, "lo_day": 8},
        {"coin_id": "bitcoin", "cycle_number": 4, "phase": "BEAR", "is_completed": 1, "is_prediction": 0, "box_index": 2, "start_x": 20, "end_x": 30, "hi": 88.0, "lo": 70.0, "hi_day": 22, "lo_day": 27},
        {"coin_id": "bitcoin", "cycle_number": 4, "phase": "BULL", "is_completed": 1, "is_prediction": 0, "box_index": 1, "start_x": 399, "end_x": 430, "hi": 26.65, "lo": 23.56, "hi_day": 399, "lo_day": 404},
        {"coin_id": "bitcoin", "cycle_number": 5, "phase": "BEAR", "is_completed": 0, "is_prediction": 0, "box_index": 1, "start_x": 2, "end_x": 4, "hi": 96.4, "lo": 88.8, "hi_day": 2, "lo_day": 4},
        {"coin_id": "bitcoin", "cycle_number": 5, "phase": "BEAR", "is_completed": 0, "is_prediction": 1, "box_index": 2, "start_x": 5, "end_x": 7, "hi": 80.1, "lo": 78.2, "hi_day": 5, "lo_day": 7},
        {"coin_id": "bitcoin", "cycle_number": 5, "phase": "BULL", "is_completed": 0, "is_prediction": 1, "box_index": 1, "start_x": 5, "end_x": 8, "hi": 90.0, "lo": 70.0, "hi_day": 5, "lo_day": 7},
    ],
}


class FakeResponse:
    def __init__(self, data):
        self.data = data


class FakeQuery:
    def __init__(self, tables, table_name):
        self.tables = tables
        self.table_name = table_name
        self.filters = []
        self.orders = []
        self.range_start = 0
        self.range_end = None
        self.limit_count = None

    def select(self, _fields):
        return self

    def eq(self, column, value):
        self.filters.append(("eq", column, value))
        return self

    def gte(self, column, value):
        self.filters.append(("gte", column, value))
        return self

    def order(self, column):
        self.orders.append(column)
        return self

    def range(self, start, end):
        self.range_start = start
        self.range_end = end
        return self

    def limit(self, count):
        self.limit_count = count
        return self

    def execute(self):
        rows = [dict(row) for row in self.tables.get(self.table_name, [])]

        for op, column, value in self.filters:
            if op == "eq":
                rows = [row for row in rows if row.get(column) == value]
            elif op == "gte":
                rows = [row for row in rows if row.get(column) is not None and row.get(column) >= value]

        for column in reversed(self.orders):
            rows.sort(key=lambda row: row.get(column))

        if self.limit_count is not None:
            rows = rows[: self.limit_count]

        if self.range_end is not None:
            rows = rows[self.range_start : self.range_end + 1]

        return FakeResponse(rows)


class FakeSupabase:
    def __init__(self, tables):
        self.tables = tables

    def table(self, name):
        return FakeQuery(self.tables, name)


class BtcChartEndpointTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def setUp(self):
        self.supabase_patch = patch("routers.btc_chart.get_supabase", return_value=FakeSupabase(FIXTURE_TABLES))
        self.supabase_patch.start()

    def tearDown(self):
        self.supabase_patch.stop()

    def test_health_endpoint_is_available(self):
        response = self.client.get("/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

    def test_ohlcv_maps_readable_time_and_volume(self):
        response = self.client.get("/api/ohlcv")
        payload = response.json()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(payload["data"]), 2)
        self.assertEqual(payload["data"][0]["readable_time"], "2026-04-18T00:00:00")
        self.assertEqual(payload["data"][1]["volume"], 765432.1)

    def test_cycle_menu_builds_labels_and_current_flag_from_actual_boxes(self):
        response = self.client.get("/api/cycle-menu")
        payload = response.json()

        self.assertEqual(response.status_code, 200)
        self.assertEqual([item["number"] for item in payload["bearCycles"]], [1, 2, 3, 4, 5])
        self.assertEqual([item["number"] for item in payload["bullCycles"]], [1, 2, 3, 4])
        self.assertEqual(payload["bearCycles"][4]["label"], "Cycle 5 (2025.10)")
        self.assertTrue(payload["bearCycles"][4]["current"])

    def test_cycle_menu_ignores_prediction_only_bull_cycle(self):
        response = self.client.get("/api/cycle-menu")
        bull_numbers = [item["number"] for item in response.json()["bullCycles"]]

        self.assertNotIn(5, bull_numbers)

    def test_cycle_comparison_groups_series_and_computes_aggregates(self):
        response = self.client.get("/api/cycle-comparison")
        payload = response.json()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(payload["series"]), 5)
        cycle_2013 = next(item for item in payload["series"] if item["name"] == "Cycle 2013")
        self.assertEqual(cycle_2013["startDate"], "2013-11-29")
        self.assertEqual(cycle_2013["minRate"], 88.0)
        self.assertEqual(cycle_2013["dayCount"], 2)
        self.assertEqual(cycle_2013["data"][-1], {"x": 2, "y": 88.0})

    def test_bear_boxes_default_cycle_returns_full_series_without_actual_bull_start(self):
        response = self.client.get("/api/bear-boxes")
        payload = response.json()

        self.assertEqual(response.status_code, 200)
        self.assertEqual([point["day"] for point in payload["lineData"]], [0, 2, 4, 5, 7])
        self.assertEqual(payload["cycleInfo"]["startDate"], "2025-10-06")
        self.assertEqual(payload["cycleInfo"]["endDate"], "2025-10-13")

    def test_bear_boxes_trims_line_data_when_actual_bull_start_exists(self):
        response = self.client.get("/api/bear-boxes?cycle=4")
        payload = response.json()

        self.assertEqual(response.status_code, 200)
        self.assertEqual([point["day"] for point in payload["lineData"]], [0, 1])

    def test_bear_boxes_maps_actual_box_offsets_to_timestamps(self):
        response = self.client.get("/api/bear-boxes?cycle=5")
        box = response.json()["boxes"][0]

        self.assertEqual(box["Start_Timestamp"], "2025-10-10T00:00:00")
        self.assertEqual(box["Peak_Timestamp"], "2025-10-08T00:00:00")
        self.assertEqual(box["End_Timestamp"], "2025-10-10T00:00:00")
        self.assertEqual(box["Start_Rate"], 88.8)
        self.assertEqual(box["Peak_Rate"], 96.4)

    def test_bear_boxes_maps_prediction_rows_separately(self):
        response = self.client.get("/api/bear-boxes?cycle=5")
        prediction = response.json()["predictions"][0]

        self.assertEqual(prediction["Start_Timestamp"], "2025-10-13T00:00:00")
        self.assertEqual(prediction["Peak_Timestamp"], "2025-10-11T00:00:00")
        self.assertEqual(prediction["End_Timestamp"], "2025-10-13T00:00:00")
        self.assertEqual(prediction["Peak_Rate"], 80.1)

    def test_bear_boxes_returns_404_for_unknown_cycle(self):
        response = self.client.get("/api/bear-boxes?cycle=9")

        self.assertEqual(response.status_code, 404)

    def test_bull_boxes_default_cycle_uses_first_actual_bull_start(self):
        response = self.client.get("/api/bull-boxes")
        payload = response.json()

        self.assertEqual(response.status_code, 200)
        self.assertEqual([point["day"] for point in payload["lineData"]], [399, 404, 430])
        self.assertEqual(payload["cycleInfo"]["maxDays"], 430)
        self.assertEqual(payload["cycleInfo"]["startDate"], "2022-12-14")

    def test_bull_boxes_maps_box_fields_from_offsets(self):
        response = self.client.get("/api/bull-boxes?cycle=4")
        box = response.json()["boxes"][0]

        self.assertEqual(box["Start_Timestamp"], "2022-12-14T00:00:00")
        self.assertEqual(box["End_Timestamp"], "2023-01-14T00:00:00")
        self.assertEqual(box["Low_Timestamp"], "2022-12-19T00:00:00")
        self.assertEqual(box["Start_Rate"], 26.65)
        self.assertEqual(box["Low_Rate"], 23.56)

    def test_bull_boxes_returns_404_when_no_actual_bull_box_exists(self):
        response = self.client.get("/api/bull-boxes?cycle=5")

        self.assertEqual(response.status_code, 404)


if __name__ == "__main__":
    unittest.main()
