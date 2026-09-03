#!/usr/bin/python -u
# vim: fileencoding=utf-8:nomodified:nowrap:textwidth=0:foldmethod=marker:foldcolumn=4:ruler:showcmd:lcs=tab\:|- list:tabstop=8:noexpandtab:nosmarttab:softtabstop=0:shiftwidth=0

import re
import sys

def process_file(input_filename):
    # Regular expression matching the pattern with capture groups for flexibility
    # Group 1: everything before the 2nd (100)
    # Group 2: everything between the 2nd and 3rd (100)
    # Group 3: everything after the 3rd (100)
    pattern = re.compile(r'^(.*)100 100(.*)100 200(.*)$')

    current_val1 = 100
    current_val2 = 100
    step = 2.54

    try:
        with open(input_filename, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.rstrip('\n')
                match = pattern.match(line)
                
                if match:
                    # Reconstruct the line with the incremented values
                    prefix = match.group(1)
                    middle = match.group(2)
                    suffix = match.group(3)
                    
                    new_line = f"{prefix}{current_val1} 0{middle}2 {current_val2}{suffix}"
                    print(new_line)
                    
                    # Increment for the next matching line
                    current_val1 += step
                    current_val2 += step
                else:
                    # Print lines that don't match as they are (optional)
                    print(line)
                    
    except FileNotFoundError:
        print(f"Error: File '{input_filename}' not found.", file=sys.stderr)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 process_file.py <filename>")
    else:
        process_file(sys.argv[1])
