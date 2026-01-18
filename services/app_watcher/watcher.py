"""App watcher service - monitors active application and switches profiles."""

import fnmatch
import subprocess
import threading
import time
from collections.abc import Callable
from pathlib import Path

from crates.profile_schema import Profile, ProfileLoader


class ActiveWindowInfo:
    """Information about the currently active window."""

    def __init__(
        self,
        pid: int | None = None,
        process_name: str | None = None,
        window_class: str | None = None,
        window_title: str | None = None,
    ):
        self.pid = pid
        self.process_name = process_name
        self.window_class = window_class
        self.window_title = window_title

    def __repr__(self) -> str:
        return (
            f"ActiveWindowInfo(pid={self.pid}, process={self.process_name}, "
            f"class={self.window_class})"
        )


class WindowBackend:
    """Base class for window monitoring backends."""

    def get_active_window(self) -> ActiveWindowInfo | None:
        """Get information about the currently active window."""
        raise NotImplementedError

    def is_available(self) -> bool:
        """Check if this backend is available on the current system."""
        raise NotImplementedError


class X11Backend(WindowBackend):
    """X11 backend using xdotool."""

    def is_available(self) -> bool:
        """Check if xdotool is available."""
        try:
            result = subprocess.run(["which", "xdotool"], capture_output=True, timeout=2)
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            return False

    def get_active_window(self) -> ActiveWindowInfo | None:
        """Get active window info using xdotool."""
        try:
            # Get active window ID
            result = subprocess.run(
                ["xdotool", "getactivewindow"], capture_output=True, text=True, timeout=2
            )
            if result.returncode != 0:
                return None

            window_id = result.stdout.strip()
            if not window_id:
                return None

            # Get window PID
            pid = None
            result = subprocess.run(
                ["xdotool", "getwindowpid", window_id], capture_output=True, text=True, timeout=2
            )
            if result.returncode == 0:
                try:
                    pid = int(result.stdout.strip())
                except ValueError:
                    pass

            # Get process name from /proc
            process_name = None
            if pid:
                try:
                    comm_path = Path(f"/proc/{pid}/comm")
                    if comm_path.exists():
                        process_name = comm_path.read_text().strip()
                except OSError:
                    pass

                # Try exe symlink as fallback
                if not process_name:
                    try:
                        exe_path = Path(f"/proc/{pid}/exe").resolve()
                        process_name = exe_path.name
                    except OSError:
                        pass

            # Get window class
            window_class = None
            result = subprocess.run(
                ["xdotool", "getwindowclassname", window_id],
                capture_output=True,
                text=True,
                timeout=2,
            )
            if result.returncode == 0:
                window_class = result.stdout.strip()

            # Get window title
            window_title = None
            result = subprocess.run(
                ["xdotool", "getwindowname", window_id], capture_output=True, text=True, timeout=2
            )
            if result.returncode == 0:
                window_title = result.stdout.strip()

            return ActiveWindowInfo(
                pid=pid,
                process_name=process_name,
                window_class=window_class,
                window_title=window_title,
            )

        except subprocess.TimeoutExpired:
            return None
        except (FileNotFoundError, OSError, ValueError):
            return None


class GnomeWaylandBackend(WindowBackend):
    """GNOME Wayland backend using gdbus."""

    def is_available(self) -> bool:
        """Check if running GNOME on Wayland."""
        import os

        session_type = os.environ.get("XDG_SESSION_TYPE", "")
        desktop = os.environ.get("XDG_CURRENT_DESKTOP", "").lower()
        return session_type == "wayland" and "gnome" in desktop

    def get_active_window(self) -> ActiveWindowInfo | None:
        """Get active window using GNOME Shell DBus."""
        try:
            # Use gdbus to query GNOME Shell
            script = """
            global.get_window_actors()
                .map(a => a.meta_window)
                .find(w => w.has_focus())
                ?.get_pid() || 0
            """
            result = subprocess.run(
                [
                    "gdbus",
                    "call",
                    "--session",
                    "--dest",
                    "org.gnome.Shell",
                    "--object-path",
                    "/org/gnome/Shell",
                    "--method",
                    "org.gnome.Shell.Eval",
                    script,
                ],
                capture_output=True,
                text=True,
                timeout=2,
            )

            if result.returncode != 0:
                return None

            # Parse result - format: (true, 'pid')
            output = result.stdout.strip()
            if "true" not in output.lower():
                return None

            # Extract PID from output
            import re

            match = re.search(r"'(\d+)'", output)
            if not match:
                return None

            pid = int(match.group(1))
            if pid == 0:
                return None

            # Get process name from /proc
            process_name = None
            try:
                comm_path = Path(f"/proc/{pid}/comm")
                if comm_path.exists():
                    process_name = comm_path.read_text().strip()
            except OSError:
                pass

            return ActiveWindowInfo(pid=pid, process_name=process_name)

        except (subprocess.TimeoutExpired, FileNotFoundError, OSError, ValueError):
            return None


class AppWatcher:
    """
    Monitors the active application and triggers profile switches.

    Usage:
        watcher = AppWatcher()
        watcher.on_profile_change = lambda profile: daemon.switch_profile(profile)
        watcher.start()
    """

    def __init__(self, config_dir: Path | None = None, poll_interval: float = 0.5):
        self.config_dir = config_dir
        self.poll_interval = poll_interval
        self.profile_loader = ProfileLoader(config_dir)

        self._backend: WindowBackend | None = None
        self._thread: threading.Thread | None = None
        self._running = False
        self._current_profile_id: str | None = None
        self._last_window_info: ActiveWindowInfo | None = None

        # Callback for profile changes
        self.on_profile_change: Callable[[Profile], None] | None = None

        # Initialize backend
        self._init_backend()

    def _init_backend(self) -> None:
        """Initialize the appropriate window monitoring backend."""
        backends = [
            GnomeWaylandBackend(),
            X11Backend(),
        ]

        for backend in backends:
            if backend.is_available():
                self._backend = backend
                print(f"App watcher using backend: {backend.__class__.__name__}")
                return

        print("Warning: No window monitoring backend available")

    def start(self) -> bool:
        """Start the app watcher thread."""
        if not self._backend:
            print("Cannot start app watcher: no backend available")
            return False

        if self._running:
            return True

        self._running = True
        self._thread = threading.Thread(target=self._watch_loop, daemon=True)
        self._thread.start()
        print("App watcher started")
        return True

    def stop(self) -> None:
        """Stop the app watcher thread."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=2)
            self._thread = None
        print("App watcher stopped")

    def _watch_loop(self) -> None:
        """Main watch loop - runs in background thread."""
        while self._running:
            try:
                self._check_active_window()
            except Exception as e:
                print(f"App watcher error: {e}")

            time.sleep(self.poll_interval)

    def _check_active_window(self) -> None:
        """Check the active window and switch profiles if needed."""
        if not self._backend:
            return

        window_info = self._backend.get_active_window()
        if not window_info:
            return

        # Check if window changed
        if (
            self._last_window_info
            and self._last_window_info.pid == window_info.pid
            and self._last_window_info.process_name == window_info.process_name
        ):
            return

        self._last_window_info = window_info

        # Find matching profile
        matching_profile = self._find_matching_profile(window_info)

        if matching_profile and matching_profile.id != self._current_profile_id:
            self._current_profile_id = matching_profile.id
            print(
                f"Switching to profile: {matching_profile.name} "
                f"(matched: {window_info.process_name})"
            )

            if self.on_profile_change:
                self.on_profile_change(matching_profile)

    def _find_matching_profile(self, window_info: ActiveWindowInfo) -> Profile | None:
        """Find a profile that matches the current window."""
        profile_ids = self.profile_loader.list_profiles()
        default_profile: Profile | None = None

        for profile_id in profile_ids:
            profile = self.profile_loader.load_profile(profile_id)
            if not profile:
                continue

            # Check if this is the default profile
            if profile.is_default:
                default_profile = profile

            # Check process name matches
            if window_info.process_name and profile.match_process_names:
                for pattern in profile.match_process_names:
                    if self._matches_pattern(window_info.process_name, pattern):
                        return profile

                    # Also check window class
                    if window_info.window_class:
                        if self._matches_pattern(window_info.window_class, pattern):
                            return profile

        # Return default profile if no match found
        return default_profile

    def _matches_pattern(self, value: str, pattern: str) -> bool:
        """Check if a value matches a pattern (supports wildcards)."""
        # Case-insensitive matching
        value_lower = value.lower()
        pattern_lower = pattern.lower()

        # Exact match
        if value_lower == pattern_lower:
            return True

        # Wildcard match using fnmatch
        if fnmatch.fnmatch(value_lower, pattern_lower):
            return True

        # Substring match
        if pattern_lower in value_lower:
            return True

        return False

    @property
    def is_running(self) -> bool:
        """Check if the watcher is running."""
        return self._running

    @property
    def backend_name(self) -> str | None:
        """Get the name of the active backend."""
        if self._backend:
            return self._backend.__class__.__name__
        return None
