#
# Copyright (c) 2012-2014, Prometheus Research, LLC
#


from setuptools import setup, find_packages


setup(
    name='rex.setup',
    version = "1.3.0",
    description="Distutils extension for the RexDB platform",
    long_description=open('README.rst', 'r').read(),
    maintainer="Prometheus Research, LLC",
    maintainer_email="contact@prometheusresearch.com",
    license="AGPLv3",
    url="https://bitbucket.org/prometheus/rex.setup",
    package_dir={'': 'src'},
    include_package_data=True,
    packages=find_packages('src'),
    namespace_packages=['rex'],
    entry_points={
        'distutils.setup_keywords': [
            'rex_init = rex.setup:check_init',
            'rex_static = rex.setup:check_static',
            'rex_download = rex.setup:check_bundle',
            'rex_bundle = rex.setup:check_bundle',
        ],
        'distutils.commands': [
            'install_static = rex.setup:install_static',
            'develop_static = rex.setup:develop_static',
            'bundle = rex.setup:bundle',
        ],
        'egg_info.writers': [
            'rex_init.txt = rex.setup:write_init',
            'rex_static.txt = rex.setup:write_static',
            'rex_bundle.txt = rex.setup:write_bundle',
        ],
    },
)


