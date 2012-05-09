#!/usr/bin/env python
import re
import sys

def parse_line(line):
    line = re.sub("\s+", " ", line.strip())
    dev, cpu_id, seq_no, ts, pid, action, rwbs, stuff = line.split(" ", 7)
    return (pid, ts, action, rwbs, stuff)

if __name__ == "__main__":
    squid_pid = None
    if len(sys.argv) > 1:
        try:
            int(sys.argv[1])
            squid_pid = str(int(sys.argv[1]))
        except ValueError:
            sys.stderr.write("Unable to interpret squid pid - defaulting to no pid filtering\n")
    for line in sys.stdin:
        try:
            pid, ts, action, rwbs, output = parse_line(line)
        except ValueError:
            continue
        if squid_pid is None or pid == squid_pid:
            if action == "D":
                sector = output.split(" ")[0]
                sys.stdout.write(",".join((pid,ts,rwbs,sector))+"\n")
