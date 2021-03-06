#
# Copyright (c) 2015, Prometheus Research, LLC
#


from setuptools import setup, find_packages


setup(
    name='rex.form_previewer_demo',
    version='0.10.6',
    description='Demo package for testing rex.form_previewer',
    package_dir={'': 'src'},
    packages=find_packages('src'),
    namespace_packages=['rex'],
    install_requires=[
        'rex.form_previewer',
        'rex.demo.forms',
    ],
    rex_init='rex.form_previewer_demo',
    rex_static='static',
)

