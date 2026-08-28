#!/usr/bin/python -u
# vim: fileencoding=utf-8:nomodified:nowrap:textwidth=0:foldmethod=marker:foldcolumn=4:ruler:showcmd:lcs=tab\:|- list:tabstop=8:noexpandtab:nosmarttab:softtabstop=0:shiftwidth=0

# from GIT-ghub/HD6309/HW-001/PLD/SOview
# 2026.08.28 03:23:20


import sys
import re

GREEN = "\033[30;102;1m"
RESET = "\033[0m"

pattern = re.compile(r'^(\d+):(.*)$')

previous = None

if len(sys.argv) != 2:
    print(f"Usage: {sys.argv[0]} file", file=sys.stderr)
    print("	enhance changes in numbered lines", file=sys.stderr)
    sys.exit(1)

with open(sys.argv[1], 'r', encoding='utf-8') as f:
    for line in f:
        text = line.rstrip('\r\n')
        newline = line[len(text):]

        match = pattern.match(text)

        # Normální řádek - beze změny
        if not match:
            print(line, end='')
            continue

        value = match.group(2)

        # První číslovaný řádek nemá s čím porovnávat
        if previous is None:
            output = value
        else:
            output = ''.join(
                f'{GREEN}{char}{RESET}'
                if i >= len(previous) or char != previous[i]
                else char
                for i, char in enumerate(value)
            )

        print(f'{match.group(1)}:{output}{newline}', end='')

        previous = value
