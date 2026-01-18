"""Macro recorder - captures key events with timing."""

import time
from collections.abc import Callable
from dataclasses import dataclass

from evdev import InputDevice, InputEvent, ecodes

from crates.keycode_map import evdev_code_to_schema
from crates.profile_schema import MacroAction, MacroStep, MacroStepType


@dataclass
class RecordedEvent:
    """A single recorded event with timestamp."""

    timestamp: float
    code: int
    value: int  # 0=up, 1=down, 2=repeat
    key_name: str


class MacroRecorder:
    """Records key events into a macro.

    Usage:
        recorder = MacroRecorder()
        recorder.start()
        # ... user presses keys ...
        macro = recorder.stop()
    """

    def __init__(
        self,
        min_delay_ms: int = 10,
        max_delay_ms: int = 5000,
        record_delays: bool = True,
        merge_press_release: bool = True,
    ):
        """Initialize recorder.

        Args:
            min_delay_ms: Minimum delay to record (ignore shorter pauses)
            max_delay_ms: Maximum delay to record (cap long pauses)
            record_delays: Whether to record delays between keys
            merge_press_release: Merge quick down+up into KEY_PRESS
        """
        self.min_delay_ms = min_delay_ms
        self.max_delay_ms = max_delay_ms
        self.record_delays = record_delays
        self.merge_press_release = merge_press_release

        self._recording = False
        self._events: list[RecordedEvent] = []
        self._start_time: float = 0
        self._on_event: Callable[[RecordedEvent], None] | None = None

    def start(self) -> None:
        """Start recording."""
        self._recording = True
        self._events = []
        self._start_time = time.time()

    def stop(self) -> MacroAction:
        """Stop recording and return the macro."""
        self._recording = False
        return self._build_macro()

    def is_recording(self) -> bool:
        """Check if currently recording."""
        return self._recording

    def record_event(self, event: InputEvent) -> bool:
        """Record a single input event.

        Args:
            event: evdev InputEvent

        Returns:
            True if event was recorded, False if ignored
        """
        if not self._recording:
            return False

        # Only record key events (not repeats by default)
        if event.type != ecodes.EV_KEY:
            return False

        if event.value == 2:  # Repeat - ignore
            return False

        # Get key name
        code_name = ecodes.KEY.get(event.code) or ecodes.BTN.get(event.code)
        if not code_name:
            return False

        if isinstance(code_name, list):
            code_name = code_name[0]

        schema_name = evdev_code_to_schema(str(code_name))

        recorded = RecordedEvent(
            timestamp=time.time(),
            code=event.code,
            value=event.value,
            key_name=schema_name,
        )

        self._events.append(recorded)

        if self._on_event:
            self._on_event(recorded)

        return True

    def set_event_callback(self, callback: Callable[[RecordedEvent], None]) -> None:
        """Set callback for when events are recorded."""
        self._on_event = callback

    def get_event_count(self) -> int:
        """Get number of recorded events."""
        return len(self._events)

    def clear(self) -> None:
        """Clear recorded events without stopping."""
        self._events = []
        self._start_time = time.time()

    def _build_macro(self) -> MacroAction:
        """Build a MacroAction from recorded events."""
        steps: list[MacroStep] = []

        if not self._events:
            return MacroAction(
                id="recorded_macro",
                name="Recorded Macro",
                steps=[],
            )

        # Process events into steps
        i = 0
        last_time = self._events[0].timestamp if self._events else 0

        while i < len(self._events):
            event = self._events[i]

            # Add delay if significant
            if self.record_delays and i > 0:
                delay_ms = int((event.timestamp - last_time) * 1000)
                if delay_ms >= self.min_delay_ms:
                    delay_ms = min(delay_ms, self.max_delay_ms)
                    steps.append(
                        MacroStep(
                            type=MacroStepType.DELAY,
                            delay_ms=delay_ms,
                        )
                    )

            # Check for quick press+release (merge into KEY_PRESS)
            if (
                self.merge_press_release
                and event.value == 1  # Key down
                and i + 1 < len(self._events)
            ):
                next_event = self._events[i + 1]
                if (
                    next_event.code == event.code
                    and next_event.value == 0  # Key up
                    and (next_event.timestamp - event.timestamp) < 0.1
                ):  # Within 100ms
                    steps.append(
                        MacroStep(
                            type=MacroStepType.KEY_PRESS,
                            key=event.key_name,
                        )
                    )
                    last_time = next_event.timestamp
                    i += 2
                    continue

            # Regular key down/up
            if event.value == 1:
                steps.append(
                    MacroStep(
                        type=MacroStepType.KEY_DOWN,
                        key=event.key_name,
                    )
                )
            elif event.value == 0:
                steps.append(
                    MacroStep(
                        type=MacroStepType.KEY_UP,
                        key=event.key_name,
                    )
                )

            last_time = event.timestamp
            i += 1

        return MacroAction(
            id="recorded_macro",
            name="Recorded Macro",
            steps=steps,
        )


class DeviceMacroRecorder(MacroRecorder):
    """Macro recorder that reads from an input device."""

    def __init__(
        self,
        device_path: str,
        stop_key: str = "ESC",
        **kwargs,
    ):
        """Initialize with a device path.

        Args:
            device_path: Path to input device (e.g., /dev/input/event0)
            stop_key: Key that stops recording (default: ESC)
        """
        super().__init__(**kwargs)
        self.device_path = device_path
        self.stop_key = stop_key.upper()
        self._device: InputDevice | None = None

    def record_from_device(
        self,
        timeout: float = 60.0,
        on_event: Callable[[RecordedEvent], None] | None = None,
    ) -> MacroAction:
        """Record from the device until stop key or timeout.

        Args:
            timeout: Maximum recording time in seconds
            on_event: Callback for each recorded event

        Returns:
            The recorded macro
        """
        if on_event:
            self.set_event_callback(on_event)

        self._device = InputDevice(self.device_path)

        try:
            self._device.grab()
            self.start()

            start = time.time()

            while self.is_recording():
                # Check timeout
                if time.time() - start > timeout:
                    break

                # Read events with timeout
                try:
                    self._device.read_one()  # Just to check if there's data
                except BlockingIOError:
                    time.sleep(0.01)
                    continue

                for event in self._device.read():
                    if event.type != ecodes.EV_KEY:
                        continue

                    # Check for stop key
                    if event.value == 1:  # Key down
                        code_name = ecodes.KEY.get(event.code)
                        if code_name:
                            if isinstance(code_name, list):
                                code_name = code_name[0]
                            schema_name = evdev_code_to_schema(str(code_name))
                            if schema_name == self.stop_key:
                                return self.stop()

                    self.record_event(event)

        finally:
            if self._device:
                try:
                    self._device.ungrab()
                except (OSError, AttributeError):
                    pass
                self._device = None

        return self.stop()
