"""Tests for MacroEditor recording feature (RecordingWorker, RecordingDialog)."""

from unittest.mock import MagicMock, patch

import pytest

from crates.profile_schema import MacroAction, MacroStep, MacroStepType


class TestRecordingWorker:
    """Tests for RecordingWorker QThread class."""

    def test_init(self):
        """Test RecordingWorker initialization."""
        from apps.gui.widgets.macro_editor import RecordingWorker

        worker = RecordingWorker(
            device_path="/dev/input/event0",
            stop_key="ESC",
            timeout=30,
        )

        assert worker.device_path == "/dev/input/event0"
        assert worker.stop_key == "ESC"
        assert worker.timeout == 30
        assert worker._should_stop is False

    def test_init_default_values(self):
        """Test RecordingWorker default initialization values."""
        from apps.gui.widgets.macro_editor import RecordingWorker

        worker = RecordingWorker("/dev/input/event0")

        assert worker.stop_key == "ESC"
        assert worker.timeout == 60

    def test_stop_sets_flag(self):
        """Test stop() sets the should_stop flag."""
        from apps.gui.widgets.macro_editor import RecordingWorker

        worker = RecordingWorker("/dev/input/event0")
        worker.stop()

        assert worker._should_stop is True

    def test_run_permission_error(self):
        """Test handling of permission error."""
        from apps.gui.widgets.macro_editor import RecordingWorker

        worker = RecordingWorker("/dev/input/event0")

        # Track signal emissions
        error_results = []
        worker.error_occurred.connect(lambda e: error_results.append(e))

        # Mock to raise PermissionError
        with patch(
            "services.macro_engine.recorder.DeviceMacroRecorder"
        ) as mock_class:
            mock_class.side_effect = PermissionError()
            worker.run()

        assert len(error_results) == 1
        assert "Permission denied" in error_results[0]
        assert "input" in error_results[0]

    def test_run_file_not_found(self):
        """Test handling of file not found error."""
        from apps.gui.widgets.macro_editor import RecordingWorker

        worker = RecordingWorker("/dev/input/event999")

        # Track signal emissions
        error_results = []
        worker.error_occurred.connect(lambda e: error_results.append(e))

        # Mock to raise FileNotFoundError
        with patch(
            "services.macro_engine.recorder.DeviceMacroRecorder"
        ) as mock_class:
            mock_class.side_effect = FileNotFoundError()
            worker.run()

        assert len(error_results) == 1
        assert "not found" in error_results[0]

    def test_run_generic_error(self):
        """Test handling of generic errors."""
        from apps.gui.widgets.macro_editor import RecordingWorker

        worker = RecordingWorker("/dev/input/event0")

        error_results = []
        worker.error_occurred.connect(lambda e: error_results.append(e))

        with patch(
            "services.macro_engine.recorder.DeviceMacroRecorder"
        ) as mock_class:
            mock_class.side_effect = RuntimeError("Something went wrong")
            worker.run()

        assert len(error_results) == 1
        assert "Something went wrong" in error_results[0]

    def test_run_success(self):
        """Test successful recording emits recording_finished."""
        from apps.gui.widgets.macro_editor import RecordingWorker

        worker = RecordingWorker("/dev/input/event0")

        finished_results = []
        worker.recording_finished.connect(lambda m: finished_results.append(m))

        mock_macro = MacroAction(
            id="test",
            name="Test",
            steps=[MacroStep(type=MacroStepType.KEY_PRESS, key="A")],
        )

        with patch(
            "services.macro_engine.recorder.DeviceMacroRecorder"
        ) as mock_class:
            mock_instance = MagicMock()
            mock_instance.record_from_device.return_value = mock_macro
            mock_class.return_value = mock_instance
            worker.run()

        assert len(finished_results) == 1
        assert finished_results[0] == mock_macro

    def test_run_emits_step_recorded(self):
        """Test that step_recorded signal is emitted during recording."""
        from apps.gui.widgets.macro_editor import RecordingWorker
        from services.macro_engine.recorder import RecordedEvent

        worker = RecordingWorker("/dev/input/event0")

        step_results = []
        worker.step_recorded.connect(lambda s: step_results.append(s))

        mock_macro = MacroAction(id="test", name="Test", steps=[])

        def fake_record(timeout, on_event):
            # Simulate recording events
            if on_event:
                event = MagicMock()
                event.key_name = "A"
                event.value = 1
                on_event(event)
            return mock_macro

        with patch(
            "services.macro_engine.recorder.DeviceMacroRecorder"
        ) as mock_class:
            mock_instance = MagicMock()
            mock_instance.record_from_device.side_effect = fake_record
            mock_class.return_value = mock_instance
            worker.run()

        assert len(step_results) == 1
        assert "A" in step_results[0]
        assert "↓" in step_results[0]


class TestRecordingDialogUnit:
    """Unit tests for RecordingDialog without requiring Qt display."""

    @pytest.fixture
    def mock_qt(self):
        """Patch Qt widgets for headless testing."""
        with patch("apps.gui.widgets.macro_editor.QDialog.__init__", return_value=None):
            with patch("apps.gui.widgets.macro_editor.QVBoxLayout"):
                with patch("apps.gui.widgets.macro_editor.QFormLayout"):
                    with patch("apps.gui.widgets.macro_editor.QHBoxLayout"):
                        with patch("apps.gui.widgets.macro_editor.QGroupBox"):
                            yield

    def test_get_recorded_macro_returns_none_initially(self):
        """Test get_recorded_macro returns None when nothing recorded."""
        from apps.gui.widgets.macro_editor import RecordingDialog

        with patch.object(RecordingDialog, "__init__", lambda self, parent=None: None):
            dialog = RecordingDialog.__new__(RecordingDialog)
            dialog._recorded_macro = None

            assert dialog.get_recorded_macro() is None

    def test_get_recorded_macro_returns_macro(self):
        """Test get_recorded_macro returns the recorded macro."""
        from apps.gui.widgets.macro_editor import RecordingDialog

        with patch.object(RecordingDialog, "__init__", lambda self, parent=None: None):
            dialog = RecordingDialog.__new__(RecordingDialog)
            dialog._recorded_macro = MacroAction(
                id="test", name="Test", steps=[]
            )

            result = dialog.get_recorded_macro()
            assert result is not None
            assert result.id == "test"


class TestRecordingDialogMethods:
    """Tests for RecordingDialog methods."""

    def test_on_recording_finished_stores_macro(self):
        """Test _on_recording_finished stores the macro."""
        from apps.gui.widgets.macro_editor import RecordingDialog

        # Create dialog instance with mocked init
        with patch.object(RecordingDialog, "__init__", lambda self, parent=None: None):
            dialog = RecordingDialog.__new__(RecordingDialog)
            dialog._recorded_macro = None
            dialog.status_label = MagicMock()
            dialog.start_btn = MagicMock()
            dialog.stop_btn = MagicMock()
            dialog.device_combo = MagicMock()
            dialog.stop_key_combo = MagicMock()
            dialog.timeout_spin = MagicMock()
            dialog.accept_btn = MagicMock()

            macro = MacroAction(
                id="test",
                name="Test",
                steps=[MacroStep(type=MacroStepType.KEY_PRESS, key="A")],
            )

            dialog._on_recording_finished(macro)

            assert dialog._recorded_macro == macro
            dialog.accept_btn.setEnabled.assert_called_with(True)

    def test_on_recording_finished_empty_macro(self):
        """Test _on_recording_finished with empty macro disables accept."""
        from apps.gui.widgets.macro_editor import RecordingDialog

        with patch.object(RecordingDialog, "__init__", lambda self, parent=None: None):
            dialog = RecordingDialog.__new__(RecordingDialog)
            dialog._recorded_macro = None
            dialog.status_label = MagicMock()
            dialog.start_btn = MagicMock()
            dialog.stop_btn = MagicMock()
            dialog.device_combo = MagicMock()
            dialog.stop_key_combo = MagicMock()
            dialog.timeout_spin = MagicMock()
            dialog.accept_btn = MagicMock()

            macro = MacroAction(id="test", name="Test", steps=[])

            dialog._on_recording_finished(macro)

            dialog.accept_btn.setEnabled.assert_called_with(False)

    def test_on_error_resets_state(self):
        """Test _on_error resets dialog state."""
        from apps.gui.widgets.macro_editor import RecordingDialog

        with patch.object(RecordingDialog, "__init__", lambda self, parent=None: None):
            dialog = RecordingDialog.__new__(RecordingDialog)
            dialog.status_label = MagicMock()
            dialog.start_btn = MagicMock()
            dialog.stop_btn = MagicMock()
            dialog.device_combo = MagicMock()
            dialog.stop_key_combo = MagicMock()
            dialog.timeout_spin = MagicMock()

            with patch("apps.gui.widgets.macro_editor.QMessageBox"):
                dialog._on_error("Test error")

            dialog.start_btn.setEnabled.assert_called_with(True)
            dialog.stop_btn.setEnabled.assert_called_with(False)

    def test_on_step_recorded_appends_to_log(self):
        """Test _on_step_recorded appends text to log."""
        from apps.gui.widgets.macro_editor import RecordingDialog

        with patch.object(RecordingDialog, "__init__", lambda self, parent=None: None):
            dialog = RecordingDialog.__new__(RecordingDialog)
            dialog.key_log = MagicMock()
            mock_scrollbar = MagicMock()
            dialog.key_log.verticalScrollBar.return_value = mock_scrollbar

            dialog._on_step_recorded("A ↓")

            dialog.key_log.append.assert_called_with("A ↓")

    def test_stop_recording_waits_for_worker(self):
        """Test _stop_recording waits for worker to finish."""
        from apps.gui.widgets.macro_editor import RecordingDialog

        with patch.object(RecordingDialog, "__init__", lambda self, parent=None: None):
            dialog = RecordingDialog.__new__(RecordingDialog)
            dialog._worker = MagicMock()
            dialog._worker.isRunning.return_value = True

            dialog._stop_recording()

            dialog._worker.stop.assert_called_once()
            dialog._worker.wait.assert_called_once_with(2000)


class TestMacroEditorRecordingIntegration:
    """Integration tests for MacroEditor._start_recording."""

    def test_start_recording_no_macro_returns_early(self):
        """Test _start_recording does nothing without a current macro."""
        from apps.gui.widgets.macro_editor import MacroEditorWidget

        with patch.object(MacroEditorWidget, "__init__", lambda self, parent=None: None):
            editor = MacroEditorWidget.__new__(MacroEditorWidget)
            editor._current_macro = None
            editor._recording = False

            # This should return early, not crash
            editor._start_recording()

            # No change expected
            assert editor._recording is False

    def test_start_recording_shows_dialog(self):
        """Test _start_recording opens RecordingDialog."""
        from apps.gui.widgets.macro_editor import MacroEditorWidget, RecordingDialog

        with patch.object(MacroEditorWidget, "__init__", lambda self, parent=None: None):
            editor = MacroEditorWidget.__new__(MacroEditorWidget)
            editor._current_macro = MacroAction(id="test", name="Test", steps=[])
            editor.record_btn = MagicMock()
            editor.record_status = MagicMock()

            with patch.object(RecordingDialog, "__init__", return_value=None) as mock_init:
                with patch.object(RecordingDialog, "exec", return_value=0):  # Rejected
                    with patch.object(RecordingDialog, "get_recorded_macro", return_value=None):
                        editor._start_recording()

            # Dialog was created
            mock_init.assert_called_once()

    def test_start_recording_replaces_steps_on_accept(self):
        """Test _start_recording replaces macro steps when dialog accepted."""
        from apps.gui.widgets.macro_editor import MacroEditorWidget, RecordingDialog

        with patch.object(MacroEditorWidget, "__init__", lambda self, parent=None: None):
            editor = MacroEditorWidget.__new__(MacroEditorWidget)
            editor._current_macro = MacroAction(
                id="test",
                name="Test",
                steps=[MacroStep(type=MacroStepType.KEY_PRESS, key="OLD")],
            )
            editor.record_btn = MagicMock()
            editor.record_status = MagicMock()
            editor.test_btn = MagicMock()
            editor._refresh_steps_list = MagicMock()
            editor._emit_macro_changed = MagicMock()

            recorded = MacroAction(
                id="recorded",
                name="Recorded",
                steps=[
                    MacroStep(type=MacroStepType.KEY_PRESS, key="NEW1"),
                    MacroStep(type=MacroStepType.KEY_PRESS, key="NEW2"),
                ],
            )

            with patch.object(RecordingDialog, "__init__", return_value=None):
                with patch.object(RecordingDialog, "exec", return_value=1):  # Accepted
                    with patch.object(RecordingDialog, "get_recorded_macro", return_value=recorded):
                        editor._start_recording()

            # Steps should be replaced
            assert len(editor._current_macro.steps) == 2
            assert editor._current_macro.steps[0].key == "NEW1"
            assert editor._current_macro.steps[1].key == "NEW2"
            editor._refresh_steps_list.assert_called_once()
            editor._emit_macro_changed.assert_called_once()

    def test_start_recording_no_steps_shows_message(self):
        """Test _start_recording shows message when no steps recorded."""
        from apps.gui.widgets.macro_editor import MacroEditorWidget, RecordingDialog

        with patch.object(MacroEditorWidget, "__init__", lambda self, parent=None: None):
            editor = MacroEditorWidget.__new__(MacroEditorWidget)
            editor._current_macro = MacroAction(id="test", name="Test", steps=[])
            editor.record_btn = MagicMock()
            editor.record_status = MagicMock()

            recorded = MacroAction(id="recorded", name="Recorded", steps=[])

            with patch.object(RecordingDialog, "__init__", return_value=None):
                with patch.object(RecordingDialog, "exec", return_value=1):  # Accepted
                    with patch.object(RecordingDialog, "get_recorded_macro", return_value=recorded):
                        editor._start_recording()

            # Should show "No steps recorded"
            editor.record_status.setText.assert_called()
            call_args = editor.record_status.setText.call_args[0][0]
            assert "No steps" in call_args or "recorded" in call_args.lower()
