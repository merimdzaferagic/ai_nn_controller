# Copyright (c) 2026 Trinity College Dublin
#
# This file is dual-licensed:
# - under the AGPL (see LICENSE)
# - under a commercial licence (contact infoknex@tcd.ie)

"""srsRAN Network Node for ai_nn_controller.

Polls InfluxDB for the latest srsRAN metrics (same data source Grafana
uses) and forwards them as measurements through the ai_nn_controller message bus.
"""

from controlled_entity import ControlledEntity, node, NodeRunner
import threading
import time
from time import sleep
from influxdb_client import InfluxDBClient


@node(name="srsRAN")
class SrsranNode(ControlledEntity):
    available_measurements = [
        "session_id",
        # UE-level metrics (from ue_info measurement)
        "pci",
        "rnti",
        "dl_bitrate",
        "ul_bitrate",
        "dl_bler",
        "ul_bler",
        "dl_mcs",
        "ul_mcs",
        "dl_nof_ok",
        "dl_nof_nok",
        "ul_nof_ok",
        "ul_nof_nok",
        "bsr",
        "cqi",
        "ri",
        "ul_snr",
        "pusch_snr_db",
        "pucch_snr_db",
        # System-level metrics (from app_resource_usage measurement)
        "cpu_usage_percent",
        "memory_usage_MB",
        "power_consumption_Watts",
    ]
    measurement_interval = 1.0

    def setup(self):
        """Start InfluxDB poller thread."""
        self._latest_metrics = {}
        self._metrics_lock = threading.Lock()

        self._influx_url = self.config.get("influxdb_url", "http://influxdb:8086")
        self._influx_token = self.config.get("influxdb_token", "")
        self._influx_org = self.config.get("influxdb_org", "srs")
        self._influx_bucket = self.config.get("influxdb_bucket", "srsran")
        self._poll_interval = int(self.config.get("poll_interval", 1))

        thread = threading.Thread(target=self._poll_influxdb, daemon=True)
        thread.start()
        print(f"[srsRAN] InfluxDB poller started: {self._influx_url} bucket={self._influx_bucket}")

    def _poll_influxdb(self):
        """Background thread polling InfluxDB for srsRAN metrics."""
        client = None
        while True:
            try:
                if client is None:
                    client = InfluxDBClient(
                        url=self._influx_url,
                        token=self._influx_token,
                        org=self._influx_org,
                    )
                    print(f"[InfluxDB] Connected to {self._influx_url}")

                query_api = client.query_api()
                measurements = {}

                # Query latest UE info
                ue_query = f'''
                    from(bucket: "{self._influx_bucket}")
                        |> range(start: -30s)
                        |> filter(fn: (r) => r._measurement == "ue_info")
                        |> last()
                '''
                ue_tables = query_api.query(ue_query)
                for table in ue_tables:
                    for record in table.records:
                        field = record.get_field()
                        value = record.get_value()
                        if isinstance(value, (int, float)):
                            measurements[field] = float(value)
                        # Extract tags
                        pci = record.values.get("pci")
                        rnti = record.values.get("rnti")
                        if pci is not None:
                            measurements["pci"] = float(pci) if str(pci).isdigit() else pci
                        if rnti is not None:
                            try:
                                measurements["rnti"] = float(int(rnti, 16))
                            except (ValueError, TypeError):
                                measurements["rnti"] = rnti

                # Query latest app_resource_usage
                res_query = f'''
                    from(bucket: "{self._influx_bucket}")
                        |> range(start: -30s)
                        |> filter(fn: (r) => r._measurement == "app_resource_usage")
                        |> last()
                '''
                res_tables = query_api.query(res_query)
                for table in res_tables:
                    for record in table.records:
                        field = record.get_field()
                        value = record.get_value()
                        if isinstance(value, (int, float)):
                            measurements[field] = float(value)

                if measurements:
                    with self._metrics_lock:
                        self._latest_metrics.update(measurements)
                    print(f"[InfluxDB] Fetched {len(measurements)} fields")
                else:
                    print("[InfluxDB] No recent metrics in bucket")

            except Exception as e:
                print(f"[InfluxDB] Error polling: {e}")
                client = None  # Reconnect on next iteration

            sleep(self._poll_interval)

    def poll_measurements(self):
        with self._metrics_lock:
            current = dict(self._latest_metrics)

        if current:
            current["session_id"] = f"session_{self.config['node_id']}_{int(time.time())}"
            return current
        return None


if __name__ == "__main__":
    NodeRunner().run()
