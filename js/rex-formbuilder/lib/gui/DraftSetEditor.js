/*
 * Copyright (c) 2015, Prometheus Research, LLC
 */

'use strict';

var React = require('react');
var ReactCreateClass = require('create-react-class');
var PropTypes = require('prop-types');
var classNames = require('classnames');

var ConfirmationModal = require('./ConfirmationModal');
var TotalFailureModal = require('./TotalFailureModal');
var {format} = require('../util');
var ElementToolbox = require('./ElementToolbox');
var ElementWorkspace = require('./ElementWorkspace').default;
var CalculationToolbox = require('./CalculationToolbox');
var CalculationWorkspace = require('./CalculationWorkspace').default;
var MenuHeader = require('./MenuHeader');
var FormSettingsModal = require('./FormSettingsModal');
var ToasterMixin = require('./ToasterMixin');
var {DraftSetActions, SettingActions, ErrorActions, I18NActions} = require('../actions');
var {DraftSetStore} = require('../stores');
var {ConfigurationError} = require('../errors');
var HTML5Backend = require('react-dnd-html5-backend');
var DragDropContext = require('react-dnd').DragDropContext;
var i18n = require('../i18n');
var _ = i18n.gettext;


var MODE_CALCULATIONS = 'CALC';
var MODE_FORM = 'FORM';


var DraftSetEditor = ReactCreateClass({
  mixins: [
    ToasterMixin
  ],

  propTypes: {
    apiBaseUrl: PropTypes.string.isRequired,
    uid: PropTypes.string,
    channels: PropTypes.arrayOf(PropTypes.string),
    instrumentMenuUrlTemplate: PropTypes.string,
    formPreviewerUrlTemplate: PropTypes.string,
    onModified: PropTypes.func
  },

  getInitialState: function () {
    return {
      editMode: MODE_FORM,
      configuration: null,
      instrumentVersion: null,
      editingSettings: false,
      publishing: false,
      modified: false,
      valid: false,
      validityError: null,
      configFailure: null
    };
  },


  componentWillMount: function () {
    SettingActions.initialize(this.props);
    I18NActions.initialize();
    if (this.props.uid) {
      DraftSetActions.activate(this.props.uid);
    }
  },

  componentWillReceiveProps: function (nextProps) {
    if (this.props.uid != nextProps.uid) {
      SettingActions.initialize(nextProps);
      if (this.props.uid) {
        DraftSetActions.activate(nextProps.uid);
      }
    }
  },

  componentDidMount: function () {
    DraftSetStore.addChangeListener(this._onDraftSetChange);
    DraftSetStore.addConfigurationFailureListener(this._onConfigFailure);
    DraftSetStore.addPublishListener(this._onPublish);
    window.addEventListener('beforeunload', this._onWindowUnload);
  },

  componentWillUnmount: function () {
    window.removeEventListener('beforeunload', this._onWindowUnload);
    DraftSetStore.removePublishListener(this._onPublish);
    DraftSetStore.removeConfigurationFailureListener(this._onConfigFailure);
    DraftSetStore.removeChangeListener(this._onDraftSetChange);
  },

  _onWindowUnload: function (event) {
    if (this.state.modified) {
      let msg = getUnsavedMessage();
      event.returnValue = msg;
      return msg;
    }
  },

  _onDraftSetChange: function () {
    var draftSet = DraftSetStore.getActive();
    var cfg = DraftSetStore.getActiveConfiguration();

    var valid = true;
    var validityError = null;
    if (cfg) {
      try {
        cfg.checkValidity();
      } catch (exc) {
        if (exc instanceof ConfigurationError) {
          valid = false;
          validityError = exc.message;
        } else {
          throw exc;
        }
      }
    }

    this.setState({
        instrumentVersion: draftSet.instrument_version,
        configuration: cfg,
        modified: DraftSetStore.activeIsModified(),
        valid: valid,
        validityError: validityError
      },
      () => this.props.onModified && this.props.onModified(this.state.modified)
    );
  },

  _onConfigFailure: function (error) {
    this.setState({
      configFailure: error.message
    });
  },

  _onPublish: function () {
    this.onReturn();
  },

  onReturn: function () {
    if (!this.props.instrumentMenuUrlTemplate) {
      return;
    }
    window.location = format(
      this.props.instrumentMenuUrlTemplate,
      {uid: this.state.instrumentVersion.instrument.uid}
    );
  },

  onModeSwitch: function () {
    if (this.state.editMode === MODE_FORM) {
      this.setState({
        editMode: MODE_CALCULATIONS
      });
    } else {
      this.setState({
        editMode: MODE_FORM
      });
    }
  },

  onSave: function () {
    if (this.state.modified && this.state.valid) {
      DraftSetActions.saveActive();
    } else if (!this.state.valid) {
      ErrorActions.report(
        _('Cannot save this Draft in its current state'),
        null,
        this.state.validityError
      );
    }
  },

  onPreview: function () {
    window.open(format(
      this.props.formPreviewerUrlTemplate,
      {
        uid: this.props.uid,
        category: 'draft'
      }
    ));
  },

  onFormSettings: function () {
    this.setState({
      editingSettings: true
    });
  },

  onSettingsDone: function () {
    this.setState({
      editingSettings: false
    });
  },

  onPublish: function () {
    this.setState({
      publishing: true
    });
  },

  onPublishAccepted: function () {
    DraftSetActions.publish();
    this.setState({
      publishing: false
    });
  },

  onPublishRejected: function () {
    this.setState({
      publishing: false
    });
  },

  renderMenuHeader: function () {
    let toggleTitle, toggleLabel;
    let toggleClasses = {'rfb-icon': true};
    if (this.state.editMode === MODE_FORM) {
      toggleTitle = _('Switch to the Calculations Editor');
      toggleLabel = _('Edit Calculations');
      toggleClasses = classNames(toggleClasses, 'icon-mode-calculations');
    } else if (this.state.editMode === MODE_CALCULATIONS) {
      toggleTitle = _('Switch to the Form Editor');
      toggleLabel = _('Edit Form');
      toggleClasses = classNames(toggleClasses, 'icon-mode-form');
    }

    let saveButtonClasses = classNames('rfb-button', {
      'rfb-button__disabled': !this.state.modified || !this.state.valid
    });

    let formTitle = null;
    if (this.state.configuration) {
      formTitle = this.state.configuration.title[
        this.state.configuration.locale
      ];
    }
    return (
      <MenuHeader
        title={formTitle}>
        {this.props.instrumentMenuUrlTemplate &&
          this.state.instrumentVersion &&
          <button
            className="rfb-button"
            onClick={this.onReturn}>
            <span className="rfb-icon icon-go-back" />
            <span>{_('Return to Menu')}</span>
          </button>
        }
        {this.state.editMode === MODE_FORM &&
          <button
            disabled={!this.state.configuration}
            className="rfb-button"
            title={_('Edit the high-level Form settings')}
            onClick={this.onFormSettings}>
            <span className="rfb-icon icon-edit" />
            <span>{_('Form Settings')}</span>
          </button>
        }
        <button
          className="rfb-button"
          title={toggleTitle}
          onClick={this.onModeSwitch}>
          <span className={toggleClasses} />
          <span>{toggleLabel}</span>
        </button>
        <button
          className={saveButtonClasses}
          title={
            this.state.validityError
            || _('Save the current state of this Draft to the database')
          }
          onClick={this.onSave}>
          <span className="rfb-icon icon-save" />
          <span>{_('Save')}</span>
        </button>
        {this.props.formPreviewerUrlTemplate &&
          <button
            disabled={this.state.modified || !this.state.valid}
            className="rfb-button"
            title={_('Explore a rendered, interactive view of this Draft')}
            onClick={this.onPreview}>
            <span className="rfb-icon icon-view" />
            <span>{_('Preview Form')}</span>
          </button>
        }
        <button
          disabled={this.state.modified || !this.state.valid}
          className="rfb-button"
          title={
            _('Publish the current state of this Draft for use by end-users')
          }
          onClick={this.onPublish}>
          <span className="rfb-icon icon-publish" />
          <span>{_('Publish')}</span>
        </button>
        <ConfirmationModal
          visible={this.state.publishing}
          onAccept={this.onPublishAccepted}
          onReject={this.onPublishRejected}>
          <p>{_(
            'Publishing this Draft will make it publicly available for use'
            + ' in data collection. Are you sure you want to publish this'
            + ' Draft?'
          )}</p>
        </ConfirmationModal>
      </MenuHeader>
    ); 
  },

  render: function () {
    let workspace;
    if (this.state.editMode === MODE_FORM) {
      workspace = (
        <div className="rfb-draftset-container">
          <ElementToolbox />
          <ElementWorkspace />
        </div>
      );
    } else if (this.state.editMode === MODE_CALCULATIONS) {
      workspace = (
        <div className="rfb-draftset-container">
          <CalculationToolbox />
          <CalculationWorkspace />
        </div>
      );
    }
    let menuHeader = this.renderMenuHeader();
    return (
      <div className="rfb-draftset-editor">
        {menuHeader}
        {this.state.configuration && this.state.editingSettings &&
          <FormSettingsModal
            ref="modalSettings"
            visible={this.state.editingSettings}
            onComplete={this.onSettingsDone}
            onCancel={this.onSettingsDone}
            />
        }
        {this.state.configFailure ?
          <div className="rfb-draftset-container">
            <TotalFailureModal visible={true}>
              <h4>This Draft Cannot Be Managed Using FormBuilder</h4>
              <p>{this.state.configFailure}</p>
              <button
                className="rfb-button"
                onClick={this.onReturn}>
                {_('Go Back')}
              </button>
            </TotalFailureModal>
          </div>
          :
          workspace
        }
        {this.renderToaster()}
      </div>
    );
  }
});

//moved from DraftSetEditor
function getUnsavedMessage() {
  return _('You\'ve made changes to this Draft, but haven\'t saved them yet.');
}

module.exports = DragDropContext(HTML5Backend)(DraftSetEditor);

