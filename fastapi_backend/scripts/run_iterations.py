import subprocess
import sys
import os

SCRIPT = os.path.join(os.path.dirname(__file__), 'run_api_tests_py.py')
PY = sys.executable

def main(n=10):
    for i in range(1, n+1):
        print(f'Iteration {i}/{n}')
        p = subprocess.run([PY, SCRIPT])
        print('returncode', p.returncode)

if __name__ == '__main__':
    main(10)
