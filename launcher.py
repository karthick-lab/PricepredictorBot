import subprocess
import sys
import os

exe_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
script_path = os.path.join(exe_dir, "gold_bot.py")

# Launch Streamlit properly
subprocess.run(["streamlit", "run", script_path])