from utils import save_tc, gen_report
import os, sys, json, re

WORKDIR = '/home/maze/workspace'
OUTDIR = '/home/maze/workspace/outputs'


def main(dest_dir):
    # Create destination directory
    os.system('mkdir -p %s' % dest_dir)

    time_file = os.path.join(WORKDIR, '.start')
    start_time = os.path.getmtime(time_file)

    # Collect testcases
    counter_tc = 1
    counter_cr = 0
    runtime = 0 # in seconds
    bug_found = False
    failed = False
    outputs_dir = OUTDIR
    time = 0

    for name in os.listdir(outputs_dir):
        if name.endswith(".foundry.log"):
            result_fp = os.path.join(outputs_dir, name)
            file_content = save_tc(dest_dir, result_fp, start_time, str(counter_tc) + '_tc')
            counter_tc = counter_tc + 1
            file_lines = file_content.split("\n")
            for file_line in file_lines:
                if not bug_found:
                    if file_line.startswith("Test result:") or file_line.startswith("Suite result:"):
                        time = re.search(r"finished in (\d+.\d+)ms", file_line)
                        if time is None:
                            time = re.search(r"finished in (\d+.\d+)s", file_line)
                            time_ms = float(time.group(1)) * 1000
                        else:
                            time_ms = float(time.group(1))
                        runtime += time_ms
                        if "FAILED" in file_line:
                            bug_found = True
                            save_tc(dest_dir, result_fp, start_time, str(counter_cr) + '_crash')
                            counter_cr += 1
            if bug_found:
                break
            if runtime == 0: # not a single test was run
                failed = True
    # Muzzle extra report
    gen_report("foundry", counter_cr, runtime, failed)
    os.system('touch /home/maze/outputs/.done')

if __name__ == '__main__':
    dest_dir = sys.argv[1]
    main(dest_dir)
