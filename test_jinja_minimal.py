from jinja2 import Environment, FileSystemLoader
import tempfile, shutil, os

# Create minimal template
tmpdir = tempfile.mkdtemp()
tpl = os.path.join(tmpdir, 'test.html')
with open(tpl, 'w', encoding='utf-8') as f:
    f.write(':root { --light: 1; }\n')
    f.write('{% if theme == "dark" -%}\n')
    f.write(':root { --dark: 2; }\n')
    f.write('{%- endif %}\n')
    f.write('body { --x: 3; }\n')

for autoescape in [False, True]:
    for trim in [False, True]:
        env = Environment(
            loader=FileSystemLoader([tmpdir]),
            autoescape=autoescape,
            trim_blocks=trim
        )
        t = env.get_template('test.html')
        r = t.render(theme='dark')
        print(f'autoescape={autoescape}, trim_blocks={trim}:')
        print(repr(r))
        print()

shutil.rmtree(tmpdir)
