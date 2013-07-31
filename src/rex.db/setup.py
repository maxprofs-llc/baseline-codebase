#
# Copyright (c) 2012-2013, Prometheus Research, LLC
#


from setuptools import setup, find_packages


setup(
    name='rex.db',
    version = "1.0.0",
    description="Database access for the RexDB platform",
    long_description=open('README.rst', 'r').read(),
    maintainer="Prometheus Research, LLC",
    maintainer_email="contact@prometheusresearch.com",
    license="AGPLv3",
    url="http://bitbucket.org/prometheus/rex.db",
    package_dir={'': 'src'},
    packages=find_packages('src'),
    namespace_packages=['rex'],
    entry_points={
        'htsql.addons': [
            'rex = htsql_rex:RexAddon',
        ],
    },
    setup_requires=[
        'rex.setup >=0.9, <2',
    ],
    install_requires=[
        'rex.web >=0.9, <2',
        'HTSQL >= 2.3.3, <2.5',
        'htsql-pgsql',
    ],
    rex_init='rex.db',
)


