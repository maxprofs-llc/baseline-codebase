/**
 * @copyright 2015, Prometheus Research, LLC
 */
'use strict';

var React       = require('react');
var qs          = require('./qs');
var resolveURL  = require('./resolveURL');

var Link = React.createClass({

  propTypes: {
    href: React.PropTypes.string.isRequired,
    params: React.PropTypes.object
  },

  render() {
    var {href, children, params, ...props} = this.props;
    if (params) {
      href = resolveURL(href) + '?' + qs.stringify(params);
    }
    return (
      <a {...props} href={href}>{children}</a>
    );
  }

});

function interpolateLinkParams(link, name, value) {
  if (!link) {
    return link;
  }
  var {params, href} = link.props;
  var nextParams = {};
  for (var n in params) {
    if (params[n] === `$${name}`) {
      nextParams[n] = value;
    } else {
      nextParams[n] = params[n];
    }
  }
  return React.cloneElement(link, {href, params: nextParams});
}

module.exports = Link;
module.exports.interpolateLinkParams = interpolateLinkParams;
