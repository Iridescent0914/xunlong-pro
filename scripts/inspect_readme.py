from pathlib import Path
b = Path('README.md').read_bytes()
print(b[:400])
print('--- as hex ---')
print(' '.join(f'{c:02X}' for c in b[:400]))
