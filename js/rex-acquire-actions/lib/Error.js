/**
 * Copyright (c) 2015, Prometheus Research, LLC
 */

import React from 'react';
import PropTypes from 'prop-types';

import {InjectI18N} from 'rex-i18n';
import * as Stylesheet from 'rex-widget/Stylesheet';
import {VBox, HBox} from '@prometheusresearch/react-box';


export default InjectI18N(class Error extends React.Component {
  static stylesheet = Stylesheet.create({
    Root: {
      Component: VBox,
    },

    Header: {
      Component: HBox,
      fontWeight: 'bold',
      fontSize: '2em',
      marginBottom: '10px',
    },

    Message: {
      Component: HBox,
    },
  });

  static propTypes = {
    message: PropTypes.string.isRequired
  };

  render() {
    let {Root, Header, Message} = this.constructor.stylesheet;
    let {title, message} = this.props;
    title = title || this._('An Error Has Occurred');

    return (
      <Root>
        <Header>{title}</Header>
        <Message>{message}</Message>
      </Root>
    );
  }
});

