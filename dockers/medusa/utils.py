import os, re
from pathlib import Path

def remove_ansi_escape(content: str) -> str:
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    result = ansi_escape.sub('', content)
    return result

def load_tc_content(file_path: Path) -> str:
    content = ""
    with open(file_path, "r") as fh:
        content = fh.read()
    content = remove_ansi_escape(content)
    return content

def save_tc(dest_dir, tc_path, start_time, sig) -> str:
    creation_time = os.path.getctime(tc_path)
    elapsed_time = creation_time - start_time
    if sig == '':
        sig = 'tc'
    name = '%011.5f_%s' % (elapsed_time, sig)
    dest_dir_path = Path(dest_dir)
    dest_dir_path.mkdir(parents=True, exist_ok=True)
    file_path = dest_dir_path / name
    content = load_tc_content(tc_path)
    with open(file_path, "w") as fh:
        fh.write(content)
    return content

# Muzzle extra report
def gen_report(tool, counter_cr, runtime, failed):
    filename = "/home/maze/outputs/report.txt"
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    with open(filename, "w") as f:
        f.write(f"{tool} report:\n")

        # amount of bugs found, should be either 1 or 0
        f.write(f"Crashes: {counter_cr}\n")

        # the runtime until the first bug was found or total time if no bug was found
        f.write(f"Time: {runtime}ms\n")

        # Whether the fuzzer failed to run the given program properly
        f.write(f"Failed: {failed}\n")
