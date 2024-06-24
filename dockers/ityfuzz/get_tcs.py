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

    for name in os.listdir(outputs_dir):
        if name.endswith(".ityfuzz.log"):
            result_fp = os.path.join(outputs_dir, name)
            file_content = save_tc(dest_dir, result_fp, start_time, str(counter_tc) + '_tc')
            counter_tc = counter_tc + 1
            if "Invariant \"echidna_noBug\" violated" in file_content:
                counter_cr += 1
        elif name.endswith('.time'):
            with open(f"{OUTDIR}/{name}","r") as time_file:
                time_line = time_file.readlines()[-1]
                runtime = float(time_line.strip()) * 1000
        elif name.endswith(".fail"):
            failed = True

    # Muzzle extra report
    gen_report("ityfuzz", counter_cr, runtime, failed)
    os.system('touch /home/maze/outputs/.done')

if __name__ == '__main__':
    dest_dir = sys.argv[1]
    main(dest_dir)
