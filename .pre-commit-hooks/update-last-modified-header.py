import sys
import re
import datetime


def replace_last_modified_date(file_path):

    with open(file_path, "r") as file:
        lines = file.readlines()

    rex = re.compile(r"(# Last modified: *)[0-9]+/[0-9]+/[0-9]+ *$")

    for i, line in enumerate(lines):
        if i > 15:
            continue
        m = rex.match(line)
        if not m:
            continue
        prefix = m.group(1)
        today = datetime.date.today().strftime("%Y/%m/%d") + "\n"
        modified_line = prefix + today
        lines[i] = modified_line

    with open(file_path, "w") as file:
        file.writelines(lines)


if __name__ == "__main__":
    for file_path in sys.argv[1:]:
        replace_last_modified_date(file_path)
