import subprocess
from pathlib import Path


def test_real_requirements(tmp_path):
    req_file = Path("requirements.txt").resolve()
    assert req_file.exists(), "requirements.txt not found"

    result = subprocess.run(["reqsync", "--path", str(req_file), "--check"], capture_output=True, text=True)
    # Log the output for debugging
    print("STDOUT:", result.stdout)
    print("STDERR:", result.stderr)

    # Fail test if reqsync exits non-zero
    assert result.returncode in (0, 11), (
        f"Unexpected exit code {result.returncode}. Output:\n{result.stdout}\n{result.stderr}"
    )
