/*
 * Copyright (c) 2015, Prometheus Research, LLC
 */

'use strict';

var deepCopy = require('deep-copy');
var EventEmitter = require('component-emitter');

var {Ajax, isEmpty} = require('../util');
var Dispatcher = require('../Dispatcher');
var constants = require('../constants');
var SettingStore = require('./SettingStore');
var I18NStore = require('./I18NStore');
var {ErrorActions, SuccessActions} = require('../actions');
var DefinitionParser = require('../DefinitionParser');
var Configuration = require('../Configuration');
var PageStart = require('../elements/PageStart');
var errors = require('../errors');
var _ = require('../i18n').gettext;


var CHANGE_EVENT = 'change';
var SAVE_EVENT = 'save';
var PUBLISH_EVENT = 'publish';
var CONFIG_FAILURE_EVENT = 'cfg-failure';

var _activeDraftSet = null;
var _activeConfiguration = null;
var _isModified = false;


/*eslint no-use-before-define:0 */

function draftToConfiguration() {
  var draftSet = _activeDraftSet;

  var forms = Object.keys(draftSet.forms).filter((key) => {
    return draftSet.forms[key].configuration !== null;
  }).map((key) => {
    return draftSet.forms[key].configuration;
  });

  var configuration;
  if ((draftSet.instrument_version.definition !== null)
      && (forms.length > 0)) {
    try {
      var calcs = null;
      if (draftSet.calculation_set !== null) {
        calcs = draftSet.calculation_set.definition;
      }
      var parser = new DefinitionParser(
        draftSet.instrument_version.definition,
        forms,
        calcs
      );
      configuration = parser.getConfiguration();
    } catch (exc) {
      if (exc instanceof errors.FormBuilderError) {
        DraftSetStore.emitConfigurationFailure(exc);
      } else {
        throw exc;
      }
    }
  } else {
    configuration = new Configuration(
      'urn:' + draftSet.instrument_version.instrument.uid,
      '1.0',
      {
        [I18NStore.getCurrentLocale()]: draftSet.instrument_version.instrument.title
      },
      I18NStore.getCurrentLocale()
    );
  }

  _activeConfiguration = configuration;
}


function configurationToDraft() {
  var config = _activeConfiguration;
  var draftSet = _activeDraftSet;

  var {instrument, form, calculations} = config.serialize();

  draftSet.instrument_version.definition = instrument;

  Object.keys(draftSet.forms).forEach((channel) => {
    draftSet.forms[channel].configuration = form;
  });

  if (!isEmpty(calculations)) {
    /*eslint camelcase:0 */
    if (isEmpty(draftSet.calculation_set)) {
      draftSet.calculation_set = {
        definition: null
      };
    }
    draftSet.calculation_set.definition = calculations;
  } else {
    draftSet.calculation_set = null;
  }
}


function activate(uid) {
  var ajax = new Ajax.Ajax({
    baseUrl: SettingStore.get('apiBaseUrl')
  });

  ajax.get(
    '/draftset/' + uid
  ).then((data) => {
    _activeDraftSet = data;
    _isModified = false;
    draftToConfiguration();
    DraftSetStore.emitChange();
  }).catch((err) => {
    ErrorActions.report(
      _('Could not retrieve Draft %(id)s', {
        id: uid
      }),
      err
    );
  });
}


var CONFIG_ATTRIBUTES = [
  'id',
  'version',
  'title',
  'locale',
  'parameters'
];

function editAttributes(attributes) {
  var updated = false;

  CONFIG_ATTRIBUTES.forEach((attr) => {
    if (attr in attributes) {
      _activeConfiguration[attr] = attributes[attr];
      updated = true;
    }
  });

  if (updated) {
    _isModified = true;
    configurationToDraft();
    DraftSetStore.emitChange();
  }
}


function findElement(element, container) {
  container = container || _activeConfiguration.elements;
  for (var i = 0; i < container.length; i++) {
    if (container[i].EID === element.EID) {
      return {
        container: container,
        index: i
      };
    } else if (container[i].questions) {
      var sub = findElement(element, container[i].questions);
      if (sub) {
        return sub;
      }
    }
  }
}


function putElement(element, afterElement, container) {
  var elm = findElement(element);
  var afterElm = afterElement ? findElement(afterElement) : null;

  if (elm) {
    elm.container.splice(elm.index, 1);
  }
  if (!afterElm) {
    container = container || _activeConfiguration.elements;
    container.push(element);
  } else {
    let index = afterElm.index;
    //we can't put before the PageStart;
    if ((afterElm.container[index] instanceof PageStart) && index == 0)
      index = 1;
    afterElm.container.splice(index, 0, element);
  }

  _isModified = true;
  configurationToDraft();
  DraftSetStore.emitChange();
}


function checkNewHome(element) {
  var newHome = findElement(element);
  var duplicateIDs = newHome.container.filter((elm) => {
    return (element.id === elm.id)
      && (element.EID !== elm.EID);
  });

  if (duplicateIDs.length > 0) {
    element.forceEdit = true;

    _isModified = true;
    configurationToDraft();
    DraftSetStore.emitChange();
  }
}


function addElement(element) {
  var elements = _activeConfiguration.elements.slice();
  elements.push(element);

  _activeConfiguration.elements = elements;
  _isModified = true;
  configurationToDraft();
  DraftSetStore.emitChange();
}


function editElement(element) {
  element.needsEdit = true;
  DraftSetStore.emitChange();
}


function cloneElement(element) {
  var result = findElement(element);
  var clone = element.clone(false, result.container);
  result.container.splice(result.index + 1, 0, clone);

  _isModified = true;
  configurationToDraft();
  DraftSetStore.emitChange();
}


function updateElement(element) {
  var result = findElement(element);
  result.container[result.index] = element;

  delete element.needsEdit;
  delete element.forceEdit;

  _isModified = true;
  configurationToDraft();
  DraftSetStore.emitChange();
}


function deleteElement(element) {
  var result = findElement(element);
  if (result) {
    result.container.splice(result.index, 1);

    _isModified = true;
    configurationToDraft();
    DraftSetStore.emitChange();
  }
}


function findCalculation(calculation) {
  for (var i = 0; i < _activeConfiguration.calculations.length; i++) {
    if (_activeConfiguration.calculations[i].CID === calculation.CID) {
      return {
        container: _activeConfiguration.calculations,
        index: i
      };
    }
  }
}


function putCalculation(calculation, afterCalculation) {
  var calc = findCalculation(calculation);
  var afterCalc = afterCalculation ? findCalculation(afterCalculation) : null;

  if (calc) {
    calc.container.splice(calc.index, 1);
  }
  if (!afterCalc) {
    _activeConfiguration.calculations.push(calculation);
  } else {
    afterCalc.container.splice(afterCalc.index, 0, calculation);
  }

  _isModified = true;
  configurationToDraft();
  DraftSetStore.emitChange();
}


function addCalculation(calculation) {
  var calculations = _activeConfiguration.calculations.slice();
  calculations.push(calculation);

  _activeConfiguration.calculations = calculations;
  _isModified = true;
  configurationToDraft();
  DraftSetStore.emitChange();
}


function editCalculation(calculation) {
  calculation.needsEdit = true;
  DraftSetStore.emitChange();
}


function cloneCalculation(calculation) {
  var result = findCalculation(calculation);
  var clone = calculation.clone(false, result.container);
  result.container.splice(result.index + 1, 0, clone);

  _isModified = true;
  configurationToDraft();
  DraftSetStore.emitChange();
}


function updateCalculation(calculation) {
  var result = findCalculation(calculation);
  result.container[result.index] = calculation;

  delete calculation.needsEdit;
  delete calculation.forceEdit;

  _isModified = true;
  configurationToDraft();
  DraftSetStore.emitChange();
}


function deleteCalculation(calculation) {
  var calculations = _activeConfiguration.calculations.slice();

  var calcIndex = -1;
  for (var i = 0; i < calculations.length; i++) {
    if (calculations[i].CID === calculation.CID) {
      calcIndex = i;
      break;
    }
  }

  if (calcIndex > -1) {
    calculations.splice(calcIndex, 1);
    _activeConfiguration.calculations = calculations;

    _isModified = true;
    configurationToDraft();
    DraftSetStore.emitChange();
  }
}


function publishActive() {
  var ajax = new Ajax.Ajax({
    baseUrl: SettingStore.get('apiBaseUrl')
  });

  ajax.post(
    '/draftset/' + _activeDraftSet.instrument_version.uid + '/publish'
  ).then(() => {
    SuccessActions.report(
      _('Draft %(id)s has been Published', {
        id: _activeDraftSet.instrument_version.uid
      })
    );
    DraftSetStore.emitPublish();
  }).catch((err) => {
    ErrorActions.report(
      _('Could not publish Draft %(id)s', {
        id: _activeDraftSet.instrument_version.uid
      }),
      err
    );
  });
}


function saveActive() {
  var ajax = new Ajax.Ajax({
    baseUrl: SettingStore.get('apiBaseUrl')
  });

  var draftSet = deepCopy(_activeDraftSet);
  delete draftSet.instrument_version.modified_by;
  delete draftSet.instrument_version.date_modified;

  ajax.put(
    '/draftset/' + draftSet.instrument_version.uid,
    draftSet
  ).then(() => {
    _isModified = false;
    SuccessActions.report(
      _('Draft %(id)s has been Saved', {
        id: _activeDraftSet.instrument_version.uid
      })
    );
    DraftSetStore.emitChange();
    DraftSetStore.emitSave();
  }).catch((err) => {
    err.response.json().then((data) => {
      ErrorActions.report(
        _('Could not save Draft %(id)s', {
          id: _activeDraftSet.instrument_version.uid
        }),
        err,
        data.error
      );
    }).catch(() => {
      ErrorActions.report(
        _('Could not save Draft %(id)s', {
          id: _activeDraftSet.instrument_version.uid
        }),
        err
      );
    });
  });
}


function getEventTargets() {
  var targets = [];
  _activeConfiguration.elements.forEach((element) => {
    targets = targets.concat(element.getEventTargets());
  });

  return targets.filter((target, idx) => {
    return (target && (targets.indexOf(target) === idx));
  });
}


function getLocaleCoverage() {
  var coverage = {
    'total': 1
  };
  I18NStore.getSupportedLocales().forEach((locale) => {
    coverage[locale.id] = isEmpty(_activeConfiguration.title[locale.id]) ? 0 : 1;
  });

  _activeConfiguration.elements.forEach((element) => {
    var cov = element.getLocaleCoverage();
    Object.keys(cov).forEach((key) => {
      coverage[key] += cov[key];
    });
  });

  return coverage
}


function getTags() {
  var tags = [];
  _activeConfiguration.elements.forEach((element) => {
    tags = tags.concat(element.getTags());
  });

  return tags.filter((tag, idx) => {
    return (tags && (tags.indexOf(tag) === idx));
  });
}


var DraftSetStore = Object.assign({}, EventEmitter.prototype, {
  getActive: function () {
    return _activeDraftSet;
  },

  getActiveConfiguration: function () {
    return _activeConfiguration;
  },

  getActiveElements: function () {
    return _activeConfiguration ? _activeConfiguration.elements : [];
  },

  getActiveCalculations: function () {
    return _activeConfiguration ? _activeConfiguration.calculations : [];
  },

  findElement: function (element) {
    return findElement(element);
  },

  findCalculation: function (calculation) {
    return findCalculation(calculation);
  },

  getEventTargets: function () {
    return getEventTargets();
  },

  getLocaleCoverage: function () {
    return getLocaleCoverage();
  },

  getTags: function () {
    return getTags();
  },

  activeIsModified: function () {
    return _isModified;
  },

  emitChange: function () {
    this.emit(CHANGE_EVENT);
  },
  addChangeListener: function (callback) {
    this.on(CHANGE_EVENT, callback);
  },
  removeChangeListener: function (callback) {
    this.removeListener(CHANGE_EVENT, callback);
  },

  emitSave: function () {
    this.emit(SAVE_EVENT);
  },
  addSaveListener: function (callback) {
    this.on(SAVE_EVENT, callback);
  },
  removeSaveListener: function (callback) {
    this.removeListener(SAVE_EVENT, callback);
  },

  emitPublish: function () {
    this.emit(PUBLISH_EVENT);
  },
  addPublishListener: function (callback) {
    this.on(PUBLISH_EVENT, callback);
  },
  removePublishListener: function (callback) {
    this.removeListener(PUBLISH_EVENT, callback);
  },

  emitConfigurationFailure: function (error) {
    this.emit(CONFIG_FAILURE_EVENT, error);
  },
  addConfigurationFailureListener: function (callback) {
    this.on(CONFIG_FAILURE_EVENT, callback);
  },
  removeConfigurationFailureListener: function (callback) {
    this.removeListener(CONFIG_FAILURE_EVENT, callback);
  },

  dispatchToken: Dispatcher.register(function (action) {
    switch (action.actionType) {
      case constants.ACTION_DRAFTSET_ACTIVATE:
        activate(action.uid);
        break;

      case constants.ACTION_DRAFTSET_EDITATTRIBUTES:
        editAttributes(action.attributes);
        break;

      case constants.ACTION_DRAFTSET_ADDELEMENT:
        addElement(action.element);
        break;

      case constants.ACTION_DRAFTSET_EDITELEMENT:
        editElement(action.element);
        break;

      case constants.ACTION_DRAFTSET_CLONEELEMENT:
        cloneElement(action.element);
        break;

      case constants.ACTION_DRAFTSET_UPDATEELEMENT:
        updateElement(action.element);
        break;

      case constants.ACTION_DRAFTSET_DELETEELEMENT:
        deleteElement(action.element);
        break;

      case constants.ACTION_DRAFTSET_PUTELEMENT:
        putElement(action.element, action.afterElement, action.container);
        break;

      case constants.ACTION_DRAFTSET_CHECKNEWHOME:
        checkNewHome(action.element);
        break;

      case constants.ACTION_DRAFTSET_ADDCALCULATION:
        addCalculation(action.calculation);
        break;

      case constants.ACTION_DRAFTSET_EDITCALCULATION:
        editCalculation(action.calculation);
        break;

      case constants.ACTION_DRAFTSET_CLONECALCULATION:
        cloneCalculation(action.calculation);
        break;

      case constants.ACTION_DRAFTSET_UPDATECALCULATION:
        updateCalculation(action.calculation);
        break;

      case constants.ACTION_DRAFTSET_DELETECALCULATION:
        deleteCalculation(action.calculation);
        break;

      case constants.ACTION_DRAFTSET_PUTCALCULATION:
        putCalculation(action.calculation, action.afterCalculation);
        break;

      case constants.ACTION_DRAFTSET_PUBLISH:
        publishActive();
        break;

      case constants.ACTION_DRAFTSET_SAVE:
        saveActive();
        break;
    }
  })
});


module.exports = DraftSetStore;

