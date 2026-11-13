"""État du moteur de capteurs intégré et présentation des indicateurs du pupitre."""
import math
import threading
import time

DEFAULT_WIDGETS = [
    {"label": "CPU", "sensor_id": "cpu_load", "secondary_sensor_id": "cpu_temp"},
    {"label": "GPU", "sensor_id": "gpu_load", "secondary_sensor_id": "gpu_temp"},
    {"label": "RAM", "sensor_id": "ram_used", "secondary_sensor_id": ""},
]

ALIASES = {
    "cpu_load": ("Charge CPU", "%"), "cpu_temp": ("Température CPU", "°C"),
    "gpu_load": ("Charge GPU", "%"), "gpu_temp": ("Température GPU", "°C"),
    "ram_used": ("RAM utilisée", "Go"),
}


class MonitoringState:
    def __init__(self):
        self._lock = threading.Lock()
        self._pending = None
        self._received_at = 0.0
        self.last_poll_timestamp = 0.0
        self.sensors = {}
        self.is_connected = False
        self.elevated = False
        self.last_metrics = {key: "--" for key in ALIASES}

    def ingest(self, snapshot):
        if snapshot.get("type") != "sensor_snapshot" or not isinstance(snapshot.get("sensors"), list):
            return
        sensors = {}
        for raw in snapshot["sensors"][:4096]:
            if not isinstance(raw, dict) or not isinstance(raw.get("id"), str):
                continue
            sensor = {key: str(raw.get(key, ""))[:256] for key in ("id", "name", "hardware", "hardware_type", "type", "unit")}
            value = raw.get("value")
            sensor["value"] = value if isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) else None
            sensors[sensor["id"]] = sensor
        with self._lock:
            self._pending = (sensors, bool(snapshot.get("elevated")), time.monotonic())

    def refresh(self):
        with self._lock:
            pending, self._pending = self._pending, None
        if pending is not None:
            self.sensors, self.elevated, self._received_at = pending
            self.last_poll_timestamp = time.time()
        self.is_connected = bool(self.sensors) and time.monotonic() - self._received_at < 6
        self.last_metrics = {key: self.format_value(self.resolve(key).get("value")) for key in ALIASES}

    def resolve(self, sensor_id):
        sensor = self.sensors.get(sensor_id)
        if sensor is None and sensor_id in ALIASES:
            predicates = {
                "cpu_load": lambda s: s["hardware_type"] == "Cpu" and s["type"] == "Load" and "total" in s["name"].lower(),
                "cpu_temp": lambda s: s["hardware_type"] == "Cpu" and s["type"] == "Temperature" and any(n in s["name"].lower() for n in ("package", "tctl/tdie")),
                "gpu_load": lambda s: s["hardware_type"].startswith("Gpu") and s["type"] == "Load" and s["name"] == "GPU Core",
                "gpu_temp": lambda s: s["hardware_type"].startswith("Gpu") and s["type"] == "Temperature" and s["name"] == "GPU Core",
                "ram_used": lambda s: s["hardware_type"] == "Memory" and s["type"] == "Data" and s["name"] == "Memory Used",
            }
            sensor = next((s for s in self.sensors.values() if predicates[sensor_id](s)), None)
        fallback = {"id": sensor_id, "name": ALIASES.get(sensor_id, ("Capteur indisponible", ""))[0], "unit": ALIASES.get(sensor_id, ("", ""))[1], "value": None}
        result = dict(sensor or fallback)
        if not self.is_connected:
            result["value"] = None
        return result

    @staticmethod
    def format_value(value):
        if value is None:
            return "--"
        return f"{value:.1f}".rstrip("0").rstrip(".").replace(".", ",")

    def payload(self, widgets):
        readings = []
        for widget in widgets:
            spec = widget.model_dump() if hasattr(widget, "model_dump") else widget
            primary = self.resolve(spec["sensor_id"])
            secondary = self.resolve(spec.get("secondary_sensor_id", ""))
            def display(sensor):
                value, unit = sensor["value"], sensor["unit"]
                if value is not None and unit == "o/s":
                    for scaled_unit in ("Ko/s", "Mo/s", "Go/s"):
                        if abs(value) < 1024:
                            break
                        value /= 1024
                        unit = scaled_unit
                return self.format_value(value), unit
            value, unit = display(primary)
            secondary_value, secondary_unit = display(secondary)
            readings.append({
                "label": spec["label"], "value": value, "unit": unit,
                "secondary_value": secondary_value if spec.get("secondary_sensor_id") else "",
                "secondary_unit": secondary_unit if spec.get("secondary_sensor_id") else "",
            })
        return {"type": "stats", "lhm_connected": self.is_connected, "data": self.last_metrics, "monitoring": readings}

    def catalog(self):
        return {
            "connected": self.is_connected, "elevated": self.elevated, "source": "integrated",
            "aliases": [{"id": key, "name": name, "unit": unit} for key, (name, unit) in ALIASES.items()],
            "sensors": sorted((dict(s, value=s["value"] if self.is_connected else None) for s in self.sensors.values()), key=lambda s: (s["hardware"], s["type"], s["name"])),
        }
