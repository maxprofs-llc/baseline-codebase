/**
 * @copyright 2015, Prometheus Research, LLC
 */

import * as KeyPath from 'rex-widget/KeyPath';
import invariant from 'invariant';
import isPlainObject from 'lodash/lang/isPlainObject';
import isArray from 'lodash/lang/isArray';
import {isEntity} from './model/Entity';

/**
 * Render object `template` with the provided `context`.
 */
export function render(template: mixed, context: Object): mixed {
  if (isArray(template)) {
    return renderArray(template, context);
  } else if (isPlainObject(template)) {
    return renderObject(template, context);
  } else {
    invariant(
      false,
      'Expected template to be an object or an array, got: %s',
      typeof template,
    );
  }
}

function renderObject(template, context) {
  let rendered = {};
  for (let key in template) {
    if (!template.hasOwnProperty(key)) {
      continue;
    }
    let item = template[key];
    if (item && item[0] === '$') {
      let value = KeyPath.get(item.substr(1), context);
      if (isEntity(value)) {
        value = value.id;
      }
      rendered[key] = value;
    } else {
      rendered[key] = item;
      if (isPlainObject(rendered[key])) {
        rendered[key] = render(rendered[key], context);
      }
    }
  }
  return rendered;
}

function renderArray(template, context) {
  let rendered = [];
  for (let i = 0; i < template.length; i++) {
    let item = render(template[i], context);
    if (!isEmptyValue(item)) {
      rendered.push(item);
    }
  }
  return rendered;
}

function isEmptyValue(obj) {
  let keys = Object.keys(obj);
  for (let i = 0; i < keys.length; i++) {
    if (obj[keys[i]] != null) {
      return false;
    }
  }
  return true;
}
