#
# Copyright (c) 2014, Prometheus Research, LLC
#


from setuptools import setup


setup(
    name='rex.expression',
    version='1.3.0',
    description='JavaScript library to parse HTSQL-like expressions',
    long_description=open('README.rst', 'r').read(),
    maintainer='Prometheus Research, LLC',
    maintainer_email='contact@prometheusresearch.com',
    license='AGPLv3',
    url='https://bitbucket.org/rexdb/rex.expression-provisional',
    include_package_data=True,
    setup_requires=[
        'rex.setup>= 1.1,<2'
    ],
    install_requires=[
        'rex.web>0.9,<4',
    ],
    rex_static='static',
)

