'use strict';

var path                 = require('path');
var webpack              = require('webpack');
var ExtractTextPlugin    = require('extract-text-webpack-plugin');
var IntrospectablePlugin = require('rex-setup/introspection/plugin');

var DEV           = !!process.env.REX_SETUP_DEV;
var BUNDLE_PREFIX = process.env.REX_SETUP_BUNDLE_PREFIX || '/bundle/';

var global_modules = path.join(
  process.env.NPM_CONFIG_PREFIX,
  'lib/bower_components');


function global(p) {
  return path.join(global_modules, p);
}

function configureWebpack(config) {
  set(config, 'watchDelay', 800);

  set(config, 'resolve.alias.react/addons', global('react/react-with-addons.js'));
  set(config, 'resolve.alias.react', global('react/react-with-addons.js'));

  set(config, 'output.path', process.cwd());
  set(config, 'output.filename', 'bundle.js');
  unshift(config, 'module.loaders', [
    {
      test: /\.js$/,
      loader: 'jsx-loader?harmony=true'
    },
    { test: /\.less$/,
      loaders: [
        ExtractTextPlugin.loader(),
        'css-loader',
        'less-loader'
      ]
    },
    { test: /\.css$/,
      loaders: [
        ExtractTextPlugin.loader(),
        'css-loader'
      ]
    },
    { test: /\.png$/, loader: 'url-loader?prefix=img/&limit=5000' },
		{ test: /\.jpg$/, loader: 'url-loader?prefix=img/&limit=5000' },
		{ test: /\.gif$/, loader: 'url-loader?prefix=img/&limit=5000' },
		{ test: /\.eot$/, loader: 'file-loader?prefix=font/' },
		{ test: /\.ttf$/, loader: 'file-loader?prefix=font/' },
		{ test: /\.svg$/, loader: 'file-loader?prefix=font/' },
		{ test: /\.woff$/, loader: 'url-loader?prefix=font/&limit=5000' }
  ]);

  unshift(config, 'resolveLoader.root', process.env.NODE_PATH);

  unshift(config, 'resolve.root', global_modules);
  set(config, 'resolve.modulesDirectories', []);
  unshift(config, 'resolve.extensions', ['', '.js']);

  unshift(config, 'plugins' ,[
    new ExtractTextPlugin('bundle.css'),
    new webpack.ResolverPlugin([
      new webpack.ResolverPlugin.DirectoryDescriptionFilePlugin(
        'bower.json', ['main'])
    ], ['normal']),
    new webpack.DefinePlugin({
      // used to guard code to run only in development
      __DEV__: DEV,
      // bundle prefix
      __BUNDLE_PREFIX__: JSON.stringify(BUNDLE_PREFIX),
      // defined as a fallback, should be defined at runtime
      __MOUNT_PREFIX__: '(typeof __MOUNT_PREFIX__ === "undefined" ? "" : __MOUNT_PREFIX__)',
      // React relies on that
      'process.env': {NODE_ENV: JSON.stringify(DEV ? 'development' : 'production')}
    }),
    new IntrospectablePlugin(),
  ]);

  return config;
}

function set(config, path, defaultValue) {
  path = path.split('.');
  path.forEach(function(p, idx) {
    if (idx === path.length - 1 && config[p] === undefined) {
      config[p] = defaultValue;
    } else {
      config[p] = config[p] || {};
      config = config[p];
    }
  });
}

function unshift(config, path, defaultValue) {
  path = path.split('.');
  path.forEach(function(p, idx) {
    if (idx === path.length - 1) {
      if (config[p] === undefined) {
        config[p] = [];
      } else if (!Array.isArray(config[p])) {
        throw new Error('invalid webpack config: ' + path + ' should be an array');
      }
      if (Array.isArray(defaultValue)) {
        config[p] = defaultValue.concat(config[p]);
      } else {
        config[p].unshift(defaultValue);
      }
    } else {
      config[p] = config[p] || {};
      config = config[p];
    }
  });
}

module.exports = {
  configureWebpack: configureWebpack
};
