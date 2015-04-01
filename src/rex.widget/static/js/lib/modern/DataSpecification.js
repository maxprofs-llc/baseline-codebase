/**
 * @copyright 2015, Prometheus Research, LLC
 */
'use strict';

var Immutable = require('immutable');
var invariant = require('rex-widget/lib/invariant');

var CANCEL_ON_UPDATE = 'CANCEL_ON_UPDATE';
var QUEUE_ON_UPDATE = 'QUEUE_ON_UPDATE';

var DEFAULT_OPTIONS = {
  strategy: CANCEL_ON_UPDATE
};

class DataSpecification {

  constructor(port, spec, options) {
    this.port = port || null;
    this.spec = spec || {};
    this.options = {...DEFAULT_OPTIONS, ...options};
  }

  bindToContext(context) {
    var params = {};
    for (var key in this.spec) {
      var spec = this.spec[key];
      if (spec instanceof Binding) {
        params = {...params, ...spec.bindToContext(context, key)};
      } else {
        params[key] = spec;
      }
    }
    return new this.constructor(this.port, params, this.options);
  }

  produceParams() {
    var params = {};
    for (var k in this.spec) {
      var v = this.spec[k];
      invariant(
        (v instanceof Value),
        'trying to produce params from unbound data specification'
      );
      if (v.options.required && v.value == null) {
        return null;
      }
      params[k] = v.value;
    }
    return Immutable.fromJS(params);
  }

  merge(other) {
    invariant(
      this.constructor === other.constructor,
      'DataSpecification.merge(): can only merge same type specifications'
    );
    invariant(
      this.port === other.port || other.port === null || this.port === null,
      'DataSpecification.merge(): can only merge specifications with the same port'
    );
    var spec = {...this.spec, ...other.spec};
    var options = {...this.options, ...other.options};
    return new this.constructor(this.port || other.port, spec, options);
  }
}

class Collection extends DataSpecification {

}

class Entity extends DataSpecification {

}

class Binding {

  constructor(options) {
    this.options = options || {};
  }
}

class StateBinding extends Binding {

  constructor(keyPath, options) {
    super(options);
    this.keyPath = keyPath;
  }

  bindToContext(context, key) {
    var bind = {};
    bind[key] = new Value(context.state[this.keyPath], this.options);
    return bind;
  }
}

class PropBinding extends Binding {

  constructor(keyPath, options) {
    super(options);
    this.keyPath = keyPath;
  }

  bindToContext(context, key) {
    var bind = {};
    bind[key] = new Value(context.props[this.keyPath], this.options);
    return bind;
  }
}

class Value {

  constructor(value, options) {
    if (value && value.valueOf) {
      value = value.valueOf();
    }
    this.value = value;
    this.options = options || {};
  }
}

module.exports = {
  DataSpecification, Collection, Entity,
  CANCEL_ON_UPDATE, QUEUE_ON_UPDATE,
  Binding, StateBinding, PropBinding,
  Value,

  /**
   * Collection specification.
   */
  collection(spec) {
    return new Collection(null, spec);
  },

  /**
   * Entity specification.
   */
  entity(spec) {
    return new Entity(null, spec);
  },

  /**
   * State binding specification.
   */
  state(keyPath, options) {
    return new StateBinding(keyPath, options);
  },

  /**
   * Prop binding specification.
   */
  prop(keyPath, options) {
    return new PropBinding(keyPath, options);
  }
};
