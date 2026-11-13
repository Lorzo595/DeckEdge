import unittest
from unittest.mock import patch

from monitoring import ALIASES, DEFAULT_WIDGETS, MonitoringState


def sensor(identifier, name, kind, value, hardware_type='Cpu', unit='°C'):
    return dict(id=identifier, name=name, type=kind, value=value,
                hardware='Composant de test', hardware_type=hardware_type, unit=unit)


class TelemetryTests(unittest.TestCase):
    def setUp(self):
        self.state = MonitoringState()

    def ingest(self, *sensors):
        self.state.ingest(dict(type='sensor_snapshot', elevated=True, sensors=list(sensors)))
        self.state.refresh()

    def test_amd_temperature(self):
        self.ingest(sensor('/cpu/temp', 'Core (Tctl/Tdie)', 'Temperature', 42.3))
        self.assertEqual(self.state.last_metrics['cpu_temp'], '42,3')

    def test_gpu_follows_each_snapshot(self):
        self.ingest(sensor('/gpu/load', 'GPU Core', 'Load', 17, 'GpuNvidia', '%'))
        self.ingest(sensor('/gpu/load', 'GPU Core', 'Load', 32, 'GpuNvidia', '%'))
        self.assertEqual(self.state.last_metrics['gpu_load'], '32')

    def test_disappearing_sensor_is_unavailable(self):
        self.ingest(sensor('/cpu/temp', 'CPU Package', 'Temperature', 40))
        self.ingest()
        self.assertEqual(self.state.last_metrics['cpu_temp'], '--')
        self.assertFalse(self.state.is_connected)

    def test_stale_data_is_not_shown_as_live(self):
        self.ingest(sensor('/cpu/temp', 'CPU Package', 'Temperature', 40))
        with patch('monitoring.time.monotonic', return_value=self.state._received_at + 7):
            self.state.refresh()
        self.assertFalse(self.state.is_connected)
        self.assertEqual(self.state.last_metrics['cpu_temp'], '--')
        self.assertIsNone(self.state.catalog()['sensors'][0]['value'])

    def test_any_sensor_can_be_rendered_and_zero_is_valid(self):
        self.ingest(sensor('/fan/0', 'Ventilateur', 'Fan', 0, 'SuperIO', 'tr/min'))
        widget = dict(label='Ventilation', sensor_id='/fan/0', secondary_sensor_id='/missing')
        reading = self.state.payload([widget])['monitoring'][0]
        self.assertEqual((reading['label'], reading['value'], reading['unit']), ('Ventilation', '0', 'tr/min'))
        self.assertEqual(reading['secondary_value'], '--')

    def test_network_rate_has_readable_units(self):
        self.ingest(sensor('/nic/0', 'Upload', 'Throughput', 2048, 'Network', 'o/s'))
        reading = self.state.payload([dict(label='Réseau', sensor_id='/nic/0')])['monitoring'][0]
        self.assertEqual((reading['value'], reading['unit']), ('2', 'Ko/s'))

    def test_ram_does_not_pick_gpu_memory(self):
        self.ingest(sensor('/gpu/data', 'Memory Used', 'Data', 4, 'GpuNvidia', 'Go'),
                    sensor('/ram/data', 'Memory Used', 'Data', 12, 'Memory', 'Go'))
        self.assertEqual(self.state.last_metrics['ram_used'], '12')

    def test_invalid_numbers_are_unavailable(self):
        self.ingest(sensor('/cpu/temp', 'CPU Package', 'Temperature', float('nan')))
        self.assertEqual(self.state.last_metrics['cpu_temp'], '--')

    def test_default_layout_is_preserved_without_sensor_discovery(self):
        payload = self.state.payload(DEFAULT_WIDGETS)
        self.assertEqual([w['label'] for w in payload['monitoring']], ['CPU', 'GPU', 'RAM'])
        self.assertTrue(all(w['value'] == '--' for w in payload['monitoring']))
        self.assertEqual(len(self.state.catalog()['aliases']), len(ALIASES))


if __name__ == '__main__':
    unittest.main()
