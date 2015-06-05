/**
 * @copyright 2015, Prometheus Research, LLC
 */
'use strict';

var React               = require('react/addons');
var cloneWithProps      = React.addons.cloneWithProps;
var emptyFunction       = require('../emptyFunction');
var BaseForm            = require('../_forms/Form');
var Value               = require('../_forms/Value');
var Button              = require('../Button');
var {VBox, HBox}        = require('../Layout');
var Port                = require('../Port');
var Query               = require('../Query');
var NotificationCenter  = require('../NotificationCenter');

var FormStyle = {
  controls: {
    marginTop: 10
  }
};

var Form = React.createClass({

  propTypes: {
    /**
     * Data specification to submit form value to.
     */
    submitTo: React.PropTypes.object,
    /**
     * Form schema in json schema format.
     */
    schema: React.PropTypes.object,
    /**
     * Initial form value.
     */
    value: React.PropTypes.object,

    /**
     * Submit button element.
     */
    submitButton: React.PropTypes.element,
    /**
     * Submit button title.
     */
    submitButtonTitle: React.PropTypes.string,

    /**
     * Callback which fires on form submit.
     *
     * This callback can alter form value before submitting it to server by
     * returning a new value.
     */
    onSubmit: React.PropTypes.func,
    /**
     * Callback which fires after form submit is complete.
     */
    onSubmitComplete: React.PropTypes.func,
    /**
     * Callback which fires if form submit results in an error.
     */
    onSubmitError: React.PropTypes.func
  },

  render() {
    var {children, schema, submitButton, submitButtonTitle, ...props} = this.props;
    var {value, submitInProgress} = this.state;
    if (submitButton) {
      var submitButtonProps = {
        type: 'button',
        onClick: this.onSubmit,
        disabled: value.params.forceShowErrors && value.allErrors || submitInProgress
      };
      if (submitButtonTitle) {
        submitButtonProps.children = submitButtonTitle;
      }
      submitButton = cloneWithProps(submitButton, submitButtonProps);
    }
    return (
      <VBox>
        <BaseForm {...props} value={value}>
          {children}
        </BaseForm>
        {submitButton &&
          <VBox style={FormStyle.controls}>
            <div>
              {submitButton}
            </div>
          </VBox>}
      </VBox>
    );
  },

  getDefaultProps() {
    return {
      submitButton: (
        <Button success>Submit</Button>
      ),
      onChange: emptyFunction.thatReturnsArgument,
      onUpdate: emptyFunction.thatReturnsArgument,
      onSubmit: emptyFunction.thatReturnsArgument,
      onSubmitComplete: emptyFunction,
      onSubmitError: emptyFunction,
      progressNotification: (
        <NotificationCenter.Notification
          kind="info"
          text="Data saving is in progress"
          icon="cog"
          ttl={Infinity}
          />
      ),
      completeNotification: (
        <NotificationCenter.Notification
          kind="success"
          text="Data saved successfully"
          icon="ok"
          />
      ),
      errorNotification: (
        <NotificationCenter.Notification
          kind="danger"
          text="There was an error while submitting data to server"
          icon="remove"
          ttl={Infinity}
          />
      )
    };
  },

  getInitialState() {
    return {
      submitInProgress: false,
      value: Value(this.props.schema, this.props.value, this.onChange)
    };
  },

  componentDidUpdate() {
    var value = this.props.onUpdate(this.state.value.value);
    if (value !== this.state.value.value) {
      this.setState({value: this.state.value.set(value, true)});
    }
  },

  componentWillReceiveProps(nextProps) {
    if (nextProps.schema !== this.props.schema) {
      var value = Value(nextProps.schema, this.state.value.value, this.onChange, this.state.value.params);
      this.setState({value});
    }
  },

  submit() {
    var {value} = this.state;
    var {submitTo, onSubmit, onSubmitComplete, onSubmitError} = this.props;
    var nextValue = value.set(
      onSubmit({...submitTo.produceParams().toJS(), ...value.value}),
      true);
    if (nextValue.allErrors) {
      this.setState({value: value.setParams({forceShowErrors: true})});
      return;
    }
    this._progressNotification = NotificationCenter.showNotification(this.props.progressNotification);
    this.setState({submitInProgress: true});
    if (submitTo.port instanceof Port) {
      if (this.props.insert) {
        submitTo.port.insert(nextValue.value).then(this.onSubmitComplete, this.onSubmitError);
      } else {
        submitTo.port.replace(this.props.value, nextValue.value).then(this.onSubmitComplete, this.onSubmitError);
      }
    } else if (submitTo.port instanceof Query) {
      submitTo.port.produce(nextValue.value).then(this.onSubmitComplete, this.onSubmitError);
    }
  },

  onChange(value) {
    value = value.set(this.props.onChange(value.value, this.state.value.value), true);
    this.setState({value});
  },

  onSubmit(e) {
    e.stopPropagation();
    e.preventDefault();
    this.submit();
  },

  onSubmitComplete() {
    this.setState({submitInProgress: false});
    NotificationCenter.removeNotification(this._progressNotification);
    NotificationCenter.showNotification(this.props.completeNotification);
    this.props.onSubmitComplete()
  },

  onSubmitError(err) {
    this.setState({submitInProgress: false});
    NotificationCenter.removeNotification(this._progressNotification);
    var errorNotification = cloneWithProps(this.props.errorNotification, {
      children: (
        <div>
          <p>Error submitting data on server:</p>
          <ErrorRenderer error={err} />
        </div>
      )
    });
    NotificationCenter.showNotification(errorNotification);
    this.props.onSubmitError()
  }
});

var ErrorRendererStyle = {
  stack: {
    whiteSpace: 'pre',
    fontFamily: 'monospace',
    overflow: 'auto'
  },
  controls: {
    textAlign: 'right'
  }
};

var ErrorRenderer = React.createClass({

  render() {
    var {error, ...props} = this.props;
    var {showDetails} = this.state;
    return (
      <div {...props}>
        <div>
          {error.message ? error.message : error.toString()}
        </div>
        {error.stack && !showDetails &&
          <div style={ErrorRendererStyle.controls}>
            <Button danger size="small" quiet onClick={this.onClick}>
              Show details
            </Button>
          </div>}
        {error.stack && showDetails &&
          <div style={ErrorRendererStyle.stack}>
            {error.stack}
          </div>}
      </div>
    );
  },

  onClick(e) {
    e.stopPropagation();
    this.setState({showDetails: true});
  },

  getInitialState() {
    return {
      showDetails: false
    };
  }
});

module.exports = Form;
