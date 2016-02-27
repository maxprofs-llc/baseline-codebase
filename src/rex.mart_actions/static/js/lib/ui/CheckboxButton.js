/**
 * @copyright 2016, Prometheus Research, LLC
 */

import React from 'react';

import {autobind, emptyFunction} from 'rex-widget/lang';
import {VBox, HBox} from 'rex-widget/layout';
import * as stylesheet from 'rex-widget/stylesheet';
import * as css from 'rex-widget/css';

let style = stylesheet.create({
  Root: {
    Component: HBox,
    flex: 1,
    cursor: css.cursor.pointer,
    padding: css.padding(5, 7),
    alignItems: 'center',
    hover: {
      background: '#EEE'
    }
  },
  Label: {
    Component: VBox,
    flex: 1,
    fontSize: '90%',
  }
});

export default class CheckboxButton extends React.Component {

  render() {
    let {value, label} = this.props;
    return (
      <style.Root  onClick={this.onClick}>
        <style.Label>{label}</style.Label>
        <VBox>
          <input type="checkbox" checked={value} onChange={emptyFunction} />
        </VBox>
      </style.Root>
    );
  }

  @autobind
  onClick() {
    let {value, onChange, name} = this.props;
    onChange(!value, name);
  }
}

