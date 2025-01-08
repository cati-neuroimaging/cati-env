import json
import os
import pathlib


conf_file = pathlib.Path(os.environ.get("SOMA_ROOT")) / "conf" / "soma-env.json"
if conf_file.exists():
    try:
        with open(conf_file) as f:
            conf = json.load(f)
        __version__ = conf.get("version")
    except Exception as e:
        print(f"ERROR: {e}")
