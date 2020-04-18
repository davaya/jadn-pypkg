from setuptools import setup, find_packages
from os import path

here = path.abspath(path.dirname(__file__))
with open(path.join(here, 'README.rst'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='jadn',
    version='0.5.0b7',
    description='JADN schema tools',
    long_description=long_description,
    long_description_content_type='text/x-rst',
    url='https://github.com/davaya/jadn-software',
    author='David Kemp',
    author_email='dk190a@gmail.com',
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: Apache Software License',
        'Operating System :: OS Independent',
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Build Tools',
    ],
    keywords='schema',
    package_dir={'': 'src'},
    packages=find_packages(where='src'),
    python_requires='>=3.4',
    install_requires=['jsonschema'],
    package_data={
        'jadn': ['jadn_schema.jadn', 'jadn_schema.json']
    }
)