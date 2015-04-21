#
# Copyright (c) 2012-2014, Prometheus Research, LLC
#


from .generate import Generate
from . import commonjs
import sys
import os
import tempfile
import pkg_resources


def webpack_config(package):
    # get a webpack config for a package or use default config bundled with
    # rex.setup
    config = commonjs.package_filename(package, 'webpack.config.js')
    if config is not None:
        return ['--config', config]
    else:
        component_path = commonjs.package_filename(package)
        # let webpack get entry via "main" key in bower.json
        entry = [component_path]
        # resolve webpack.config.js installed as a part of rex-setup package
        config = commonjs.node([
            '-p',
            'require.resolve("rex-setup/webpack.config.js")'
        ], quiet=True).strip()
        return [
            '--config', config,
            '--context', component_path
        ] + entry


def webpack(module, target):
    cwd = commonjs.package_filename(module)
    return commonjs.node([
        commonjs.find_executable('webpack'),
        '--bail',
        '--optimize-minimize',
        '--devtool', 'source-map',
        '--output-path', target
    ] + webpack_config(module), cwd=cwd)


def webpack_watch(module, target):
    env = {'REX_SETUP_DEV': '1'}
    cwd = commonjs.package_filename(module)
    return commonjs.node([
        commonjs.find_executable('webpack'),
        '--devtool', 'eval',
        '--output-path', target,
        '--hide-modules',
        '--watch'
    ] + webpack_config(module), cwd=cwd, daemon=True, env=env)


class GenerateWebpack(Generate):
    # Packs CommonJS modules for client-side usage.

    scheme = 'webpack'

    def __call__(self):
        # If the package is being installed from a repository
        # with `python setup.py install`, our CommonJS packages
        # has not been installed yet.
        commonjs.install_package(self.dist, skip_if_installed=True)
        # Build the bundle.
        webpack(self.dist, self.target)

    def watch(self):
        # If we are at this point, the package has been installed
        # with `python setup.py develop` and so CommonJS packages
        # must have been installed already.
        proc = webpack_watch(self.dist, self.target)
        def terminate():
            try:
                proc.terminate()
            except OSError:
                # The server process must have died already.
                pass
        return terminate

