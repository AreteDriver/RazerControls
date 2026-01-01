"""Tests for the app watcher service."""

from unittest.mock import MagicMock, patch

import pytest

from services.app_watcher import ActiveWindowInfo, AppWatcher, GnomeWaylandBackend, X11Backend


class TestActiveWindowInfo:
    """Tests for ActiveWindowInfo dataclass."""

    def test_creation(self):
        """Test creating window info."""
        info = ActiveWindowInfo(pid=1234, process_name="firefox")
        assert info.pid == 1234
        assert info.process_name == "firefox"
        assert info.window_class is None
        assert info.window_title is None

    def test_full_creation(self):
        """Test creating window info with all fields."""
        info = ActiveWindowInfo(
            pid=1234,
            process_name="firefox",
            window_class="Navigator",
            window_title="Mozilla Firefox",
        )
        assert info.pid == 1234
        assert info.process_name == "firefox"
        assert info.window_class == "Navigator"
        assert info.window_title == "Mozilla Firefox"

    def test_repr(self):
        """Test string representation."""
        info = ActiveWindowInfo(pid=1234, process_name="firefox", window_class="Navigator")
        repr_str = repr(info)
        assert "1234" in repr_str
        assert "firefox" in repr_str


class TestPatternMatching:
    """Tests for pattern matching in AppWatcher."""

    @pytest.fixture
    def watcher(self):
        """Create a watcher instance for testing."""
        with patch.object(AppWatcher, "_init_backend"):
            watcher = AppWatcher()
            watcher._backend = None
            return watcher

    def test_exact_match(self, watcher):
        """Test exact string matching."""
        assert watcher._matches_pattern("firefox", "firefox") is True
        assert watcher._matches_pattern("Firefox", "firefox") is True  # Case insensitive
        assert watcher._matches_pattern("chrome", "firefox") is False

    def test_wildcard_match(self, watcher):
        """Test wildcard pattern matching."""
        assert watcher._matches_pattern("firefox", "fire*") is True
        assert watcher._matches_pattern("firefox", "*fox") is True
        assert watcher._matches_pattern("game.exe", "*.exe") is True
        assert watcher._matches_pattern("game.bin", "*.exe") is False

    def test_substring_match(self, watcher):
        """Test substring matching."""
        assert watcher._matches_pattern("steam_app_12345", "steam") is True
        assert watcher._matches_pattern("com.google.chrome", "chrome") is True

    def test_case_insensitive(self, watcher):
        """Test case insensitive matching."""
        assert watcher._matches_pattern("FIREFOX", "firefox") is True
        assert watcher._matches_pattern("Firefox", "FIREFOX") is True
        assert watcher._matches_pattern("steam_app", "Steam") is True


class TestX11Backend:
    """Tests for X11 backend."""

    def test_is_available_with_xdotool(self):
        """Test availability check when xdotool exists."""
        backend = X11Backend()
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            assert backend.is_available() is True

    def test_is_available_without_xdotool(self):
        """Test availability check when xdotool doesn't exist."""
        backend = X11Backend()
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1)
            assert backend.is_available() is False

    def test_get_active_window_success(self):
        """Test getting active window info."""
        backend = X11Backend()

        def mock_run(cmd, **kwargs):
            result = MagicMock()
            if cmd[1] == "getactivewindow":
                result.returncode = 0
                result.stdout = "12345678"
            elif cmd[1] == "getwindowpid":
                result.returncode = 0
                result.stdout = "1234"
            elif cmd[1] == "getwindowclassname":
                result.returncode = 0
                result.stdout = "Navigator"
            elif cmd[1] == "getwindowname":
                result.returncode = 0
                result.stdout = "Firefox"
            else:
                result.returncode = 1
            return result

        with patch("subprocess.run", side_effect=mock_run):
            with patch("pathlib.Path.exists", return_value=True):
                with patch("pathlib.Path.read_text", return_value="firefox\n"):
                    info = backend.get_active_window()

        assert info is not None
        assert info.pid == 1234
        assert info.process_name == "firefox"
        assert info.window_class == "Navigator"
        assert info.window_title == "Firefox"

    def test_get_active_window_no_window(self):
        """Test when no window is active."""
        backend = X11Backend()
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1)
            info = backend.get_active_window()
            assert info is None


class TestGnomeWaylandBackend:
    """Tests for GNOME Wayland backend."""

    def test_is_available_on_gnome_wayland(self):
        """Test availability on GNOME Wayland."""
        backend = GnomeWaylandBackend()
        env = {"XDG_SESSION_TYPE": "wayland", "XDG_CURRENT_DESKTOP": "GNOME"}
        with patch.dict("os.environ", env):
            assert backend.is_available() is True

    def test_is_available_on_x11(self):
        """Test availability on X11."""
        backend = GnomeWaylandBackend()
        with patch.dict("os.environ", {"XDG_SESSION_TYPE": "x11", "XDG_CURRENT_DESKTOP": "GNOME"}):
            assert backend.is_available() is False

    def test_is_available_on_kde(self):
        """Test availability on KDE."""
        backend = GnomeWaylandBackend()
        env = {"XDG_SESSION_TYPE": "wayland", "XDG_CURRENT_DESKTOP": "KDE"}
        with patch.dict("os.environ", env):
            assert backend.is_available() is False


class TestAppWatcher:
    """Tests for the main AppWatcher class."""

    def test_start_without_backend(self):
        """Test starting watcher without a backend."""
        with patch.object(AppWatcher, "_init_backend"):
            watcher = AppWatcher()
            watcher._backend = None
            assert watcher.start() is False

    def test_is_running(self):
        """Test is_running property."""
        with patch.object(AppWatcher, "_init_backend"):
            watcher = AppWatcher()
            watcher._backend = None
            assert watcher.is_running is False

    def test_backend_name_none(self):
        """Test backend_name when no backend."""
        with patch.object(AppWatcher, "_init_backend"):
            watcher = AppWatcher()
            watcher._backend = None
            assert watcher.backend_name is None

    def test_backend_name_x11(self):
        """Test backend_name with X11 backend."""
        with patch.object(AppWatcher, "_init_backend"):
            watcher = AppWatcher()
            watcher._backend = X11Backend()
            assert watcher.backend_name == "X11Backend"

    def test_stop_when_not_running(self):
        """Test stopping when not running."""
        with patch.object(AppWatcher, "_init_backend"):
            watcher = AppWatcher()
            watcher._backend = None
            watcher.stop()  # Should not raise
            assert watcher.is_running is False
