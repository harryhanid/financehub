"""Layout of the HO Report, extracted from the Excel master into ho_template.json."""
import functools
import json
import os

_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ho_template.json")


@functools.lru_cache(maxsize=1)
def load_template() -> dict:
    with open(_PATH, encoding="utf-8") as f:
        return json.load(f)
