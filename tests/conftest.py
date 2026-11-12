"""Skip test modules that need the ML extra (torch) when it is not installed, as on CI."""

import importlib.util

collect_ignore: list[str] = []
if importlib.util.find_spec("torch") is None:
    collect_ignore += [
        "test_ema.py",
        "test_limit_groups.py",
        "test_rescale_aug.py",
        "test_tta.py",
    ]
