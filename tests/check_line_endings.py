"""Reject CRLF/mixed text in Git's index and working tree on all platforms."""
import subprocess

lines = subprocess.check_output(['git', 'ls-files', '--eol'], text=True).splitlines()
invalid = [line for line in lines if any(flag in line.split('\t', 1)[0].split()
           for flag in ('i/crlf', 'i/mixed', 'w/crlf', 'w/mixed'))]
if invalid:
    raise SystemExit('Text files must use LF:\n' + '\n'.join(invalid))
print(f'OK: {len(lines)} tracked files checked; no CRLF or mixed line endings.')
