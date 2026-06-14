import os
import sys
import subprocess
import time
import glob
from typing import Dict, Any, List

from app.config import WORKSPACE_DIR, ARTIFACTS_DIR
CODE_DIR = os.path.join(WORKSPACE_DIR, "code")

os.makedirs(CODE_DIR, exist_ok=True)
os.makedirs(ARTIFACTS_DIR, exist_ok=True)

def execute_python_code(code: str, timeout_seconds: int = 15) -> Dict[str, Any]:
    """
    Executes Python code in a subprocess.
    Captures stdout, stderr, execution time, and any newly generated files in the artifacts directory.
    """
    timestamp = int(time.time())
    code_filename = f"run_{timestamp}.py"
    code_path = os.path.join(CODE_DIR, code_filename)
    
    # Premium chart styling configuration injected at the top of the file
    premium_styling = """# --- Premium Matplotlib Styling ---
try:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams['figure.facecolor'] = '#ffffff'
    plt.rcParams['axes.facecolor'] = '#ffffff'
    plt.rcParams['savefig.facecolor'] = '#ffffff'
    plt.rcParams['axes.edgecolor'] = '#e2e8f0'
    plt.rcParams['axes.linewidth'] = 1.0
    plt.rcParams['axes.grid'] = True
    plt.rcParams['grid.color'] = '#f1f5f9'
    plt.rcParams['grid.linestyle'] = '--'
    plt.rcParams['grid.linewidth'] = 0.7
    plt.rcParams['xtick.color'] = '#64748b'
    plt.rcParams['ytick.color'] = '#64748b'
    plt.rcParams['text.color'] = '#1e293b'
    plt.rcParams['axes.labelcolor'] = '#334155'
    plt.rcParams['axes.titlecolor'] = '#0f172a'
    plt.rcParams['axes.titlesize'] = 13
    plt.rcParams['axes.titleweight'] = 'bold'
    plt.rcParams['axes.titlepad'] = 14
    plt.rcParams['legend.frameon'] = True
    plt.rcParams['legend.facecolor'] = '#ffffff'
    plt.rcParams['legend.edgecolor'] = '#e2e8f0'
    plt.rcParams['legend.fontsize'] = 9
    plt.rcParams['axes.spines.top'] = False
    plt.rcParams['axes.spines.right'] = False
    
    # Premium color palette (Teal, Amber, Rose, Mint, Indigo)
    colors = ['#20808d', '#eab308', '#ec4899', '#10b981', '#6366f1']
    plt.rcParams['axes.prop_cycle'] = matplotlib.cycler(color=colors)
    
    # Customize line and marker defaults
    plt.rcParams['lines.linewidth'] = 2.2
    plt.rcParams['lines.markersize'] = 6
    
    # Intercept savefig to ensure tight_layout, clean background and high resolution
    _orig_savefig = plt.savefig
    def _premium_savefig(*args, **kwargs):
        kwargs.setdefault('facecolor', '#ffffff')
        kwargs.setdefault('bbox_inches', 'tight')
        kwargs.setdefault('dpi', 180)
        try:
            plt.tight_layout()
        except Exception:
            pass
        return _orig_savefig(*args, **kwargs)
    plt.savefig = _premium_savefig
except Exception:
    pass
# ----------------------------------
"""
    # Save the code to a file
    with open(code_path, "w", encoding="utf-8") as f:
        f.write(premium_styling + "\n" + code)
        
    # Get files in artifacts directory before run
    pre_files = set(glob.glob(os.path.join(ARTIFACTS_DIR, "*")))
    
    # Run the code
    start_time = time.time()
    try:
        # Use sys.executable to run inside the same virtual environment
        result = subprocess.run(
            [sys.executable, code_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout_seconds,
            cwd=WORKSPACE_DIR # Run in the workspace directory context
        )
        
        stdout = result.stdout
        stderr = result.stderr
        exit_code = result.returncode
        success = (exit_code == 0)
        
    except subprocess.TimeoutExpired as e:
        stdout = e.stdout if e.stdout else ""
        stderr = f"Execution timed out after {timeout_seconds} seconds.\n" + (e.stderr if e.stderr else "")
        exit_code = -1
        success = False
    except Exception as e:
        stdout = ""
        stderr = f"Subprocess run error: {e}"
        exit_code = -1
        success = False
        
    execution_time = time.time() - start_time
    
    # Get files in artifacts directory after run
    post_files = set(glob.glob(os.path.join(ARTIFACTS_DIR, "*")))
    new_files = post_files - pre_files
    
    # Also look in the workspace root directory for images, move them to artifacts
    workspace_root_files = glob.glob(os.path.join(WORKSPACE_DIR, "*.png")) + \
                           glob.glob(os.path.join(WORKSPACE_DIR, "*.jpg")) + \
                           glob.glob(os.path.join(WORKSPACE_DIR, "*.csv"))
    
    for f in workspace_root_files:
        filename = os.path.basename(f)
        dest = os.path.join(ARTIFACTS_DIR, filename)
        try:
            # Move file to artifacts
            os.rename(f, dest)
            new_files.add(dest)
        except Exception as e:
            stderr += f"\nError moving artifact {filename} to artifacts folder: {e}"
            
    # Format artifacts list as relative names
    artifacts = [os.path.basename(f) for f in new_files]
    
    return {
        "success": success,
        "stdout": stdout,
        "stderr": stderr,
        "exit_code": exit_code,
        "execution_time_seconds": round(execution_time, 2),
        "artifacts": artifacts
    }
