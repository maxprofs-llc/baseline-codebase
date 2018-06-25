/**
 * @copyright 2016, Prometheus Research, LLC
 */

import React, {PropTypes} from 'react';

import {InjectI18N} from 'rex-i18n';

import * as FormContext from './FormContext';
import isReactElement from '../isReactElement';
import getLocalizedString from '../getLocalizedString';

const textStyle = {
  width: '100%',
  display: 'inline-block',
  wordWrap: 'break-word',
  whiteSpace: 'normal',
};

@InjectI18N
export default class LocalizedString extends React.Component {

  static propTypes = {
    text: PropTypes.oneOfType([
      PropTypes.string,
      PropTypes.object
    ]).isRequired,
  };

  static contextTypes = FormContext.contextTypes;

  static defaultProps = {
    Component: 'span',
  };

  render() {
    let {Component, text, ...props} = this.props;

    let localizedText;
    if (isReactElement(text)) {
      localizedText = text;
    } else {
      localizedText = getLocalizedString(
        text,
        this.getI18N(),
        this.context.defaultLocalization,
      );
    }

    return (
      <Component style={{...textStyle, ...props.style}} {...props}>
        {localizedText}
      </Component>
    );
  }
}
