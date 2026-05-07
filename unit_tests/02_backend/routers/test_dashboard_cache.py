import os
import threading
import time
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from main import app
from routers import chart


FIXTURE_TABLES = {
    "coins": [
        {"id": "bitcoin", "symbol": "BTC", "name": "Bitcoin", "rank": 1},
        {"id": "ethereum", "symbol": "ETH", "name": "Ethereum", "rank": 2},
        {"id": "emptycoin", "symbol": "EMP", "name": "Empty Coin", "rank": 3},
    ],
    "alt_cycle_data": [
        {
            "coin_id": "bitcoin",
            "cycle_number": 1,
            "cycle_name": "Cycle 2021",
            "days_since_peak": 0,
            "close_rate": 100,
            "high_rate": 102,
            "low_rate": 98,
            "peak_date": "2021-11-10",
            "peak_price": 69000,
            "timestamp": "2021-11-10T00:00:00",
        },
        {
            "coin_id": "bitcoin",
            "cycle_number": 2,
            "cycle_name": "Current Cycle (2025)",
            "days_since_peak": 0,
            "close_rate": 100,
            "high_rate": 101,
            "low_rate": 99,
            "peak_date": "2025-10-06",
            "peak_price": 120000,
            "timestamp": "2025-10-06T00:00:00",
        },
        {
            "coin_id": "ethereum",
            "cycle_number": 1,
            "cycle_name": "Cycle 2025",
            "days_since_peak": 0,
            "close_rate": 100,
            "high_rate": 100,
            "low_rate": 100,
            "peak_date": "2025-10-06",
            "peak_price": 4500,
            "timestamp": "2025-10-06T00:00:00",
        },
    ],
    "coin_analysis_results": [
        {
            "coin_id": "bitcoin",
            "cycle_number": 2,
            "box_index": 1,
            "phase": "BEAR",
            "result": "ACTIVE",
            "start_x": 0,
            "end_x": 1,
            "hi": 100,
            "lo": 90,
            "hi_day": 0,
            "lo_day": 1,
            "duration": 1,
            "range_pct": 10,
            "is_prediction": 0,
            "is_completed": 0,
            "rise_days": None,
            "decline_days": None,
        },
        {
            "coin_id": "ethereum",
            "cycle_number": 1,
            "box_index": 1,
            "phase": "BEAR",
            "result": "ACTIVE",
            "start_x": 0,
            "end_x": 1,
            "hi": 100,
            "lo": 90,
            "hi_day": 0,
            "lo_day": 1,
            "duration": 1,
            "range_pct": 10,
            "is_prediction": 0,
            "is_completed": 0,
            "rise_days": None,
            "decline_days": None,
        }
    ],
    "coin_prediction_paths": [
        {
            "coin_id": "bitcoin",
            "cycle_number": 2,
            "scenario": "bull",
            "day_x": 1,
            "value": 105,
        }
    ],
    "coin_prediction_peaks": [
        {
            "coin_id": "bitcoin",
            "cycle_number": 2,
            "peak_type": "bull",
            "predicted_value": 140,
            "predicted_day": 30,
        }
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

    def select(self, _fields):
        return self

    def eq(self, column, value):
        self.filters.append((column, value))
        return self

    def order(self, column):
        self.orders.append(column)
        return self

    def range(self, start, end):
        self.range_start = start
        self.range_end = end
        return self

    def execute(self):
        rows = [dict(row) for row in self.tables.get(self.table_name, [])]
        for column, value in self.filters:
            rows = [row for row in rows if row.get(column) == value]
        for column in reversed(self.orders):
            rows.sort(key=lambda row: row.get(column))
        if self.range_end is not None:
            rows = rows[self.range_start : self.range_end + 1]
        return FakeResponse(rows)


class FakeSupabase:
    def __init__(self, tables):
        self.tables = tables

    def table(self, name):
        return FakeQuery(self.tables, name)


class DashboardCacheEndpointTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def setUp(self):
        chart._DASHBOARD_SNAPSHOT_CACHE["snapshot"] = None
        chart._DASHBOARD_SNAPSHOT_CACHE["created_at"] = 0.0
        self.supabase_patch = patch(
            "routers.chart.get_supabase", return_value=FakeSupabase(FIXTURE_TABLES)
        )
        self.mock_get_supabase = self.supabase_patch.start()
        self.secret_patch = patch.dict(
            os.environ, {"DASHBOARD_CACHE_REFRESH_SECRET": "secret"}, clear=False
        )
        self.secret_patch.start()

    def tearDown(self):
        self.secret_patch.stop()
        self.supabase_patch.stop()
        chart._DASHBOARD_SNAPSHOT_CACHE["snapshot"] = None
        chart._DASHBOARD_SNAPSHOT_CACHE["created_at"] = 0.0

    def test_dashboard_data_keeps_legacy_shape_without_top_level_meta(self):
        response = self.client.get("/api/dashboard-data")
        payload = response.json()

        self.assertEqual(response.status_code, 200)
        self.assertIn("bitcoin", payload)
        self.assertNotIn("data_version", payload)
        self.assertNotIn("generated_at", payload)
        self.assertEqual(payload["bitcoin"]["cycles"][1]["cycle_number"], 2)

    def test_dashboard_data_force_refresh_query_does_not_bypass_cache(self):
        first = self.client.get("/api/dashboard-data")
        second = self.client.get("/api/dashboard-data?force_refresh=true")

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(self.mock_get_supabase.call_count, 1)

    def test_manifest_and_initial_data_are_snapshot_projections_with_meta(self):
        manifest_response = self.client.get("/api/dashboard-manifest")
        initial_response = self.client.get("/api/dashboard-initial-data")

        manifest = manifest_response.json()
        initial = initial_response.json()

        self.assertEqual(manifest_response.status_code, 200)
        self.assertEqual(initial_response.status_code, 200)
        self.assertEqual(manifest["default_coin_id"], "bitcoin")
        self.assertEqual(manifest["default_cycle_number"], 2)
        self.assertIn("data_version", manifest)
        self.assertEqual(initial["data"]["bitcoin"]["cycles"][0]["cycle_number"], 2)
        self.assertEqual(initial["data"]["ethereum"]["cycles"], [])
        self.assertEqual(initial["data"]["emptycoin"]["cycles"], [])

    def test_cycle_data_returns_requested_cycle_from_snapshot(self):
        response = self.client.get(
            "/api/dashboard-cycle-data?coin_id=ethereum&cycle_number=1"
        )
        payload = response.json()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(payload["coin_id"], "ethereum")
        self.assertEqual(payload["symbol"], "ETH")
        self.assertEqual(payload["cycle"]["cycle_number"], 1)
        self.assertIn("cache_status", payload)

    def test_cycle_data_returns_404_for_unknown_manifest_cycle(self):
        response = self.client.get(
            "/api/dashboard-cycle-data?coin_id=ethereum&cycle_number=9"
        )

        self.assertEqual(response.status_code, 404)

    def test_internal_refresh_requires_secret(self):
        response = self.client.post(
            "/api/internal/dashboard-cache/refresh",
            headers={"X-Internal-Secret": "wrong"},
        )

        self.assertEqual(response.status_code, 403)

    def test_internal_refresh_with_secret_builds_snapshot(self):
        response = self.client.post(
            "/api/internal/dashboard-cache/refresh",
            headers={"X-Internal-Secret": "secret"},
        )
        payload = response.json()

        self.assertEqual(response.status_code, 200)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["cache_status"], "refreshed")
        self.assertIsNotNone(chart._DASHBOARD_SNAPSHOT_CACHE["snapshot"])

    def test_refresh_build_failure_keeps_existing_snapshot(self):
        self.client.get("/api/dashboard-manifest")
        previous_snapshot = chart._DASHBOARD_SNAPSHOT_CACHE["snapshot"]

        with patch("routers.chart._build_dashboard_snapshot", side_effect=RuntimeError):
            response = self.client.post(
                "/api/internal/dashboard-cache/refresh",
                headers={"X-Internal-Secret": "secret"},
            )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["ok"])
        self.assertEqual(response.json()["cache_status"], "stale_kept")
        self.assertIs(chart._DASHBOARD_SNAPSHOT_CACHE["snapshot"], previous_snapshot)

    def test_cold_cache_build_failure_returns_error(self):
        with patch("routers.chart._build_dashboard_snapshot", side_effect=RuntimeError):
            response = self.client.get("/api/dashboard-manifest")

        self.assertEqual(response.status_code, 503)

    def test_concurrent_cold_cache_requests_share_single_build(self):
        snapshot = {
            "data_version": "snapshot-test",
            "generated_at": "2026-05-07T00:00:00Z",
            "data": {},
            "manifest": {"default_coin_id": None, "default_cycle_number": None, "coins": []},
        }
        build_count = 0
        build_count_lock = threading.Lock()

        def slow_build():
            nonlocal build_count
            with build_count_lock:
                build_count += 1
            time.sleep(0.05)
            return snapshot

        results = []

        def request_snapshot():
            results.append(chart._get_or_build_dashboard_snapshot())

        with patch("routers.chart._build_dashboard_snapshot", side_effect=slow_build):
            threads = [threading.Thread(target=request_snapshot) for _ in range(3)]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join()

        self.assertEqual(build_count, 1)
        self.assertEqual(len(results), 3)
        self.assertTrue(all(result[0] is snapshot for result in results))


if __name__ == "__main__":
    unittest.main()
