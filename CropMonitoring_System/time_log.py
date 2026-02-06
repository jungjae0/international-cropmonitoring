from datetime import datetime
import os

base_path = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(base_path, "cron_test_output.txt"), "a") as f:
    f.write(f"CRON TEST executed at {datetime.now()}\n")
