/*
 * Copyright (c) 2016, Prometheus Research, LLC
 */


import React from 'react';

import I18NContexted from './I18NContexted';


@I18NContexted
export default class FormatTime extends React.Component {
  render() {
    let date = this.context.RexI18N.formatTime(
      this.props.value,
      this.props.format
    );
    let Wrapper = this.props.wrapper || 'span';

    return (
      <Wrapper>{date}</Wrapper>
    );
  }
}


FormatTime.propTypes = {
  value: React.PropTypes.instanceOf(Date).isRequired,
  format: React.PropTypes.string,
  wrapper: React.PropTypes.element
};


FormatTime.defaultProps = {
  format: 'medium'
};
