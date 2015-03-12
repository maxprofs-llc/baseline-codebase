/*
 * Copyright (c) 2015, Prometheus Research, LLC
 */

'use strict';

var objectPath = require('object-path');

var Numeric = require('./Numeric');
var _ = require('../../i18n').gettext;


class Float extends Numeric {
  static getName() {
    return _('Float');
  }

  serialize(instrument, form) {
    return super(instrument, form, 'float');
  }
}


Numeric.registerElement(Float, function (element, instrument, field) {
  if (field.type.rootType === 'float') {
    var elm = new Float();
    elm.parse(element, instrument, field);
    return elm;
  }
});


module.exports = Float;

