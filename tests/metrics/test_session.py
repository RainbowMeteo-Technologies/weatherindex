

from unittest.mock import MagicMock, mock_open, patch
from metrics.session import Session


class TestSession:
    def test_session_smoke(self):
        session = Session(session_path="test",
                          start_time=0,
                          end_time=100)

        assert session.start_time == 0
        assert session.end_time == 100
        assert session.data_folder == "test/data"
        assert session.tables_folder == "test/tables"
        assert session.session_name == "test"
        assert session.forecast_range == 7800
        assert session.sensors_folder == "test/sensors"
        assert session.metrics_folder == "test/metrics"

    @patch("builtins.open", new_callable=mock_open)
    def test_session_from_folder(self, mock_open):
        session = Session(session_path="test",
                          start_time=0,
                          end_time=100)

        data = None

        def _read():
            nonlocal data
            return data

        def _write(payload):
            nonlocal data
            data = payload

        mock_open.return_value.read = _read
        mock_open.return_value.write = _write

        session.save_meta()
        new_sesssion = Session.create_from_folder("test")

        assert session.start_time == new_sesssion.start_time
        assert session.end_time == new_sesssion.end_time
        assert session.data_folder == new_sesssion.data_folder
        assert session.tables_folder == new_sesssion.tables_folder
        assert session.session_name == new_sesssion.session_name
        assert session.forecast_range == new_sesssion.forecast_range
        assert session.sensors_folder == new_sesssion.sensors_folder
        assert session.metrics_folder == new_sesssion.metrics_folder

    @patch("metrics.session.os.remove")
    @patch("metrics.session.os.walk")
    def test_clear_outdated(self, os_walk_mock, os_rm_mock: MagicMock):
        session = Session(session_path="test",
                          start_time=0,
                          end_time=100)

        os_walk_mock.return_value = [("test/", (), ("100.zip", "99.zip", "60.zip", "102.zip"))]
        session._clear_outdated(target_dir="test",
                                deadline=100)

        print(os_rm_mock.call_args_list)
        removed_zips = []
        for args, _ in os_rm_mock.call_args_list:
            removed_zips.append(args[0])

        assert removed_zips == ["test/99.zip", "test/60.zip"]
