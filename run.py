#!/usr/bin/env python3
"""兼容入口：等价于 python -m arcaea_rhythm build。"""

from arcaea_rhythm.pipeline import main

if __name__ == "__main__":
    raise SystemExit(main())
