"""Exception locations without exception text or source content."""

import os
import traceback


def safe_traceback(error: BaseException) -> str:
    frames = [
        f'  File "{os.path.basename(frame.f_code.co_filename)}", line {line}, in {frame.f_code.co_name}'
        for frame, line in traceback.walk_tb(error.__traceback__)
    ]
    return "\n".join(
        ["Traceback (most recent call last):", *frames, type(error).__name__]
    )
