import os, sys, csv, re

def main(experiment_outputs, output_dir):
    tool_results = []
    test_programs = os.listdir(experiment_outputs)
    tool_dirs = []
    for test_program_dir in test_programs:
        if tool_dirs == []:
            tool_dirs = os.listdir(os.path.join(experiment_outputs, test_program_dir))
        for tool_subdir in tool_dirs:
            crashes_line = ""
            runtime_line = ""
            failed_line = "1"
            tool_rep_file = os.path.join(experiment_outputs, test_program_dir, tool_subdir, "outputs", "report.txt")
            if os.path.exists(tool_rep_file):
                # read report file and extract data to write to csv
                with open(tool_rep_file, "r") as f:
                    file_lines = f.readlines()
                    crashes_line = file_lines[1].replace("Crashes: ", "").strip()
                    crashes_line = "1" if int(crashes_line) > 0 else "0"
                    runtime_line = file_lines[2].replace("Time: ", "").strip().replace("ms", "")
                    failed_line = file_lines[3].replace("Failed: ", "").strip()
                    failed_line = "1" if failed_line == "True" else "0"

            # extract seed parsed to fuzzer from tool subdirectory name
            test_program_setting = test_program_dir.strip().split("-")
            algorithm, size, gen_seed, _, cycle_percentage = test_program_setting[:5]
            method = "-".join(test_program_setting[5:])
            width, height = size.split("x")
            cycle_percentage = cycle_percentage.replace("percent", "")
            tool, epoch, fuzz_seed = tool_subdir.split("-")
            tool_results.append([tool, algorithm, width, height, gen_seed, cycle_percentage, method, fuzz_seed, epoch, crashes_line, failed_line, runtime_line])

    res_f = open(os.path.join(output_dir, "results_file.csv"), "w+")
    writer = csv.writer(res_f)

    headline = (["tool", "algorithm", "width", "height", "genSeed", "cyclePercentage", "method", "fuzzSeed", "epoch", "bugFound", "crash", "timeMs"])
    writer.writerow(headline)

    for row in tool_results:
        writer.writerow(row)
    res_f.close()

if __name__ == "__main__":
    experiment_outputs = sys.argv[1]
    output_dir = sys.argv[2]
    main(experiment_outputs, output_dir)