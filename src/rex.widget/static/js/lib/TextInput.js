/**
 * @jsx React.DOM
 */
'use strict';

var React             = require('react/addons');
var cx                = React.addons.classSet;
var PropTypes         = React.PropTypes;
var emptyFunction     = require('./emptyFunction');
var AmortizedOnChange = require('./AmortizedOnChange');

var TextInput = React.createClass({
  mixins: [AmortizedOnChange],

  propTypes: {
    value: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
    onValue: PropTypes.func,
    placeholder: PropTypes.string,
    disabled: PropTypes.bool,
    textarea: PropTypes.bool
  },

  render() {
    var value = this.getValue();
    var component = this.props.textarea ? React.DOM.textarea : React.DOM.input;
    var className = cx({
      'rex-widget-TextInput': true,
      'rex-widget-TextInput--textarea': this.props.textarea,
      'rex-widget-TextInput--verticalResize': this.props.textarea && this.props.resize === 'vertical',
      'rex-widget-TextInput--horizontalResize': this.props.textarea && this.props.resize === 'horizontal',
      'rex-widget-TextInput--noResize': this.props.textarea && this.props.resize === 'none'
    });
    return this.transferPropsTo(
      <component
        className={className}
        placeholder={this.props.placeholder}
        value={value}
        disabled={this.props.disabled}
        onChange={this.onChange}
        />
    );
  },

  getDefaultProps() {
    return {
      onValue: emptyFunction,
      value: null,
      placeholder: undefined
    };
  },

  getInitialState() {
    return this.getStateFromProps(this.props);
  },

  getStateFromProps({value}) {
    return {value};
  },

  getValue() {
    if (this.state.value !== null) {
      return this.state.value;
    }
    return this.props.value;
  },

  onChangeImmediate(e) {
    var value = e.target.value === '' ? null : e.target.value;
    this.setState({value});
  },

  onChangeAmortized(e) {
    var value = e.target.value === '' ? null : e.target.value;
    if (this.props.value !== value) {
      this.props.onValue(value, e.target.id);
    }
  }

});

module.exports = TextInput;
