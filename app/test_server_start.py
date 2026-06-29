#!/usr/bin/env python
"""Quick test to check if the server banner works and mDNS is registered."""

import os
import sys
import subprocess
import time
import signal

os.environ["FH_JWT_SECRET"] = "thisisareallylongsecretkeywith64characterstomakeitvalid12345"
os.environ["PYTHONIOENCODING"] = "utf-8"

# Run server in a subprocess and capture output
proc = subprocess.Popen(
    [sys.executable, "run_production.py"],
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True,
    bufsize=1
)

output_lines = []
try:
    # Capture first few lines of output
    for i in range(15):
        line = proc.stdout.readline()
        if line:
            output_lines.append(line.rstrip())
            print(line.rstrip())
        else:
            break
except Exception as e:
    print(f"Error reading output: {e}")
finally:
    # Kill the process
    try:
        os.kill(proc.pid, signal.SIGTERM)
    except:
        pass

# Check output for critical strings
banner_found = any("Finance Hub — Production Server" in line for line in output_lines)
mdns_ok = any("✓" in line for line in output_lines)
domain_line = [line for line in output_lines if "Domain" in line]

print("\n=== VERIFICATION ===")
print(f"Banner found: {banner_found}")
print(f"mDNS check mark found: {mdns_ok}")
if domain_line:
    print(f"Domain line: {domain_line[0]}")
    if "http://financehub.local:" in domain_line[0]:
        print("✓ Domain line has correct format")
    else:
        print("✗ Domain line format incorrect")
else:
    print("✗ No Domain line found")

if banner_found and mdns_ok:
    print("\n✓ VERIFICATION PASSED")
    sys.exit(0)
else:
    print("\n✗ VERIFICATION FAILED")
    sys.exit(1)
