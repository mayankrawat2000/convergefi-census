import os
import shutil
import pytest
from app.executor import execute_python_code, ARTIFACTS_DIR

def test_execute_python_success():
    code = """
import pandas as pd
print("Hello from python executor")
    """
    res = execute_python_code(code)
    assert res["success"] is True
    assert "Hello from python executor" in res["stdout"]
    assert res["exit_code"] == 0

def test_execute_python_syntax_error():
    code = """
print("Forgot parentheses"
    """
    res = execute_python_code(code)
    assert res["success"] is False
    assert "SyntaxError" in res["stderr"]
    assert res["exit_code"] != 0

def test_execute_python_runtime_error():
    code = """
x = 10 / 0
    """
    res = execute_python_code(code)
    assert res["success"] is False
    assert "ZeroDivisionError" in res["stderr"]
    assert res["exit_code"] != 0

def test_execute_python_timeout():
    code = """
import time
time.sleep(3)
    """
    # Run with small timeout
    res = execute_python_code(code, timeout_seconds=1)
    assert res["success"] is False
    assert "timed out" in res["stderr"]

def test_execute_python_artifacts():
    code = """import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
plt.figure()
plt.plot([1, 2], [3, 4])
plt.savefig("test_plot_123.png")"""
    res = execute_python_code(code)
    assert res["success"] is True, f"Execution failed with stderr: {res['stderr']}"
    
    # Check that artifact was created and moved
    artifact_path = os.path.join(ARTIFACTS_DIR, "test_plot_123.png")
    assert os.path.exists(artifact_path)
    assert "test_plot_123.png" in res["artifacts"]
    
    # Clean up
    if os.path.exists(artifact_path):
        os.remove(artifact_path)
