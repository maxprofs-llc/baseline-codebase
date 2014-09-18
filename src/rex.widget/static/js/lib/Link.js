/**
 * Link component which provides a React component API to Sitemap.
 *
 * @jsx React.DOM
 */
'use strict';

var React     = require('react');
var PropTypes = React.PropTypes;
var invariant = require('./invariant');
var Sitemap   = require('./Sitemap');

var Link = React.createClass({

  propTypes: {
    href: PropTypes.string,
    to: PropTypes.string,
    params: PropTypes.object,
    unsafe: PropTypes.bool,
    plain: PropTypes.bool
  },

  render() {
    return this.transferPropsTo(
      <a className="rex-widget-Link" href={this.href()}>
        {this.props.children || this.props.text}
      </a>
    );
  },

  href() {
    var {unsafe, plain, params, href, to} = this.props;
    invariant(
      href || to,
      '<Link /> component should be provide either ' +
      'with "href" or "to" prop'
    );
    invariant(
      !(href && to),
      '<Link /> component cannot be provide with ' +
      '"href" and "to" props at the same time'
    );
    invariant(
      !(to && unsafe),
      '<Link /> component cannot be provide with ' +
      '"to" and "unsafe" props at the same time'
    );
    if (to) {
      return Sitemap.linkTo(to, params, {plain});
    } else if (unsafe) {
      return Sitemap.linkUnsafe(href, params, {plain});
    } else {
      return Sitemap.link(href, params, {plain});
    }
  }
});

module.exports = Link;
