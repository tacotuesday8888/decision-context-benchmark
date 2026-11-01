"""Wait for the existing serial Astra process, then finish Luna without changing routes."""
import fcntl
from pathlib import Path
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[2]
with (ROOT/'results/expanded-execution/.run.lock').open('a') as lock:
    fcntl.flock(lock,fcntl.LOCK_EX)
    result=subprocess.run([sys.executable,str(ROOT/'scripts/expanded_execution/execute.py'),'eval','--config','luna_chat'],cwd=ROOT)
    if result.returncode:raise SystemExit(result.returncode)
    subprocess.run([sys.executable,str(ROOT/'scripts/expanded_execution/analyze.py')],cwd=ROOT,check=True)
