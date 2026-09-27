#!/usr/bin/env python3
"""OMP regression battery for the Attio-Merlin proxy (port 18092).

Runs 4 agent scenarios through `omp -p` against attio-merlin/attio-claude-4.6-sonnet
and prints PASS/FAIL verdicts. Each run takes 2-4 min; total ~10-12 min.

Usage: python _omp_battery.py [--quick]
  --quick  run only tests A and B (~5 min)

Exit code: number of failed tests (0 = all pass).
"""
import re
import subprocess
import sys

MODEL = 'attio-merlin/attio-claude-4.6-sonnet'
CWD = r'C:\Users\User'

TESTS = [
    ('A', 'read',
     'покажи первые 5 строк файла C:/Users/User/tmp/attio_proxy/_health.mjs',
     [r'fetch\(', r'status:']),
    ('B', 'bash',
     'выполни команду: покажи список файлов *.mjs в папке C:/Users/User/tmp/attio_proxy и их количество',
     [r'smoke']),
    ('C', 'multi-step',
     'найди в папке C:/Users/User/tmp/attio_proxy все файлы .mjs, посчитай их, и назови 3 самых больших по размеру',
     [r'server\.mjs', r'\d+']),
    ('D', 'error-recovery',
     'покажи содержимое файла C:/Users/User/tmp/attio_proxy/nonexistent-xyz-123.txt',
     [r'(?i)не\s*существ|not\s*exist|нет\s*такого|найден']),
]
REFUSAL = re.compile(
    r'(?i)я не могу|не могу открыть|нет доступа к|prompt injection|'
    r'I can.?t (help|access|open)|Attio workflow|JSON-манифест',
)

def run_omp(task: str) -> str:
    proc = subprocess.run(
        ['omp', '-p', f'--model={MODEL}', task],
        cwd=CWD, capture_output=True, text=True, encoding='utf-8',
        errors='replace', timeout=285)
    return (proc.stdout or '') + (proc.stderr or '')




def verdict(output: str, needles) -> str:
    hits = sum(1 for n in needles if re.search(n, output))
    leaked = bool(REFUSAL.search(output))
    if hits and not leaked:
        return 'PASS'
    if hits and leaked:
        return 'PASS-LEAK'  # right data, legend leaked into reply
    return 'FAIL'


def main() -> int:
    quick = '--quick' in sys.argv
    tests = TESTS[:2] if quick else TESTS
    failures = 0
    for tid, name, task, needles in tests:
        print(f'[{tid}] {name}: running...', flush=True)
        out = run_omp(task)
        tail = '\n'.join(out.strip().splitlines()[-6:])
        status = verdict(out, needles)
        if not status.startswith('PASS'):
            failures += 1
        print(f'[{tid}] {name}: {status}\n{tail}\n', flush=True)
    print(f'BATTERY: {len(tests) - failures}/{len(tests)} passed')
    return failures


if __name__ == '__main__':
    sys.exit(main())
