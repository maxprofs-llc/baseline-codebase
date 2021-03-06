/*
 * Copyright (c) 2015, Prometheus Research, LLC
 */

'use strict';

var React = require('react');
var PropTypes = require('prop-types');
var ReactCreateClass = require('create-react-class');

var ModalMixin = require('./Modal');
var PropertyEditor = require('./PropertyEditor');
var _ = require('../i18n').gettext;


var PropertyEditorModalInner = ReactCreateClass({
  mixins: [
    ModalMixin
  ],

  propTypes: {
    element: PropTypes.object.isRequired,
    isSubElement: PropTypes.bool,
    onComplete: PropTypes.func
  },

  getDefaultProps: function () {
    return {
      onComplete: function () {},
      isSubElement: false,
      className: 'rfb-property-editor-modal'
    };
  },

  onSubmit: function () {
    if (this.refs.editor.checkValid()) {
      var props = this.refs.editor.getProperties();
      var element = this.props.element.clone(true);
      Object.keys(props).forEach((prop) => {
        element[prop] = props[prop];
      });

      this.props.onComplete(element);
    }
  },

  onCancel: function () {
    this.props.onCancel();
  },

  reset: function () {
    this.refs.editor.reset();
  },

  renderModalContent: function () {
    return (
      <div>
        <h3>{this.props.element.constructor.getName()}</h3>
        <PropertyEditor
          ref="editor"
          element={this.props.element}
          isSubElement={this.props.isSubElement}
          />

        <div className="rfb-modal-actions">
          <button
            className="rfb-button"
            onClick={this.onSubmit}>
            {_('Update')}
          </button>
          {this.props.canCancel &&
            <button
              className="rfb-button"
              onClick={this.onCancel}>
              {_('Cancel')}
            </button>
          }
        </div>
      </div>
    );
  }
});


var PropertyEditorModal = ReactCreateClass({
  reset: function () {
    this.refs.inner.reset();
  },

  render: function () {
    return (
      <PropertyEditorModalInner
        ref="inner"
        canCancel={!this.props.element.forceEdit}
        {...this.props}
        />
    );
  }
});


module.exports = PropertyEditorModal;

