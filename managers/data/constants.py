"""Constants shared by the data managers."""
from __future__ import annotations

import os

# Project root /data, unless DATA_DIR is set (Docker sets /app/data).
DEFAULT_DATA_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data")
