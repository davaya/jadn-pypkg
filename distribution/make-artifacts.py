"""
Translate each schema file in Source directory to multiple formats in Out directory
"""
import jadn
import os
import shutil
from typing import NoReturn

SCHEMA_DIR = 'Schemas'
OUTPUT_DIR = 'Out'


def translate(filename: str, sdir: str, odir: str) -> NoReturn:
    fn, ext = os.path.splitext(filename)
    try:
        loader = {
            '.jadn': jadn.load,
            '.jidl': jadn.convert.jidl_load,
            '.html': jadn.convert.html_load
        }[ext]
    except KeyError:
        print(f'Unsupported schema format: {filename}')
        return

    schema = loader(os.path.join(sdir, filename))
    print(f'{filename:}:')
    print('\n'.join([f'{k:>15}: {v}' for k, v in jadn.analyze(jadn.check(schema)).items()]))

    jadn.dump(schema, os.path.join(odir, fn + '.jadn'))
    jadn.dump(jadn.transform.unfold_extensions(jadn.transform.strip_comments(schema)),
              os.path.join(odir, fn + '_core.jadn'))
    jadn.convert.dot_dump(schema, os.path.join(odir, fn + '.dot'), style={'links': True})
    jadn.convert.plant_dump(schema, os.path.join(odir, fn + '.puml'), style={'links': True, 'detail': 'information'})
    jadn.convert.jidl_dump(schema, os.path.join(odir, fn + '.jidl'), style={'desc': 48, 'page': 120})
    jadn.convert.html_dump(schema, os.path.join(odir, fn + '.html'))
    jadn.convert.table_dump(schema, os.path.join(odir, fn + '.md'))
    jadn.translate.json_schema_dump(schema, os.path.join(odir, fn + '.json'))


if __name__ == '__main__':
    print(f'Installed JADN version: {jadn.__version__}\n')
    css_dir = os.path.join(OUTPUT_DIR, 'css')
    os.makedirs(css_dir, exist_ok=True)
    shutil.copy(os.path.join(jadn.data_dir(), 'dtheme.css'), css_dir)
    for f in os.listdir(SCHEMA_DIR):
        translate(f, SCHEMA_DIR, OUTPUT_DIR)
