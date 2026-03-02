"""
Long-press exit handler for Whisplay apps.

Drop-in helper that detects a sustained button hold (default 5 s) and
lets the app show a confirmation prompt before exiting back to the
Whisplay Launcher.

Usage (inside any Whisplay app):
    from exit_helper import LongPressExit

    handler = LongPressExit(
        board,
        on_press=my_on_button_press,
        shutdown_fn=my_shutdown,
    )

    # In your game loop each frame:
    if handler.check_long_press():
        # show confirmation UI, then call handler.exit_to_launcher()
        ...
"""

import time
import sys

HOLD_SECONDS = 5.0


class LongPressExit:
    """Wraps WhisPlayBoard button callbacks with a long-press exit detector."""

    def __init__(self, board, on_press=None, on_release=None,
                 shutdown_fn=None, hold_seconds=HOLD_SECONDS):
        self._board = board
        self._user_on_press = on_press
        self._user_on_release = on_release
        self._shutdown_fn = shutdown_fn
        self._hold_seconds = hold_seconds
        self._press_start = None

        board.on_button_press(self._handle_press)
        board.on_button_release(self._handle_release)

    def _handle_press(self):
        self._press_start = time.time()
        if self._user_on_press:
            self._user_on_press()

    def _handle_release(self):
        self._press_start = None
        if self._user_on_release:
            self._user_on_release()

    def check_long_press(self):
        """Call each frame. Returns True once when hold duration is reached."""
        if self._press_start is not None:
            if time.time() - self._press_start >= self._hold_seconds:
                self._press_start = None
                return True
        return False

    def exit_to_launcher(self):
        if self._shutdown_fn:
            self._shutdown_fn()
        else:
            sys.exit(0)
