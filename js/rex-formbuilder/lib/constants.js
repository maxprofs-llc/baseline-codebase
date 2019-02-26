/*
 * Copyright (c) 2015, Prometheus Research, LLC
 */

'use strict';


var Constants = {
  ACTION_SETTING_INITIALIZE: 'SETTING_INIT',

  ACTION_I18N_INITIALIZE: 'I18N_INIT',

  ACTION_ERROR_REPORT: 'ERROR_REPORT',
  ACTION_SUCCESS_REPORT: 'SUCCESS_REPORT',

  ACTION_INSTRUMENT_CREATE: 'INST_CREATE',
  ACTION_INSTRUMENT_ACTIVATE: 'INST_ACTIVATE',
  ACTION_INSTRUMENT_DEACTIVATE: 'INST_DEACTIVATE',

  ACTION_INSTRUMENTVERSION_CLONE: 'IV_CLONE',

  ACTION_DRAFTSET_ACTIVATE: 'DS_ACTIVATE',
  ACTION_DRAFTSET_EDITATTRIBUTES: 'DS_EDITATTR',
  ACTION_DRAFTSET_ADDELEMENT: 'DS_ADDELEMENT',
  ACTION_DRAFTSET_EDITELEMENT: 'DS_EDITELEMENT',
  ACTION_DRAFTSET_CLONEELEMENT: 'DS_CLONEELEMENT',
  ACTION_DRAFTSET_PUTELEMENT: 'DS_PUTELEMENT',
  ACTION_DRAFTSET_CHECKNEWHOME: 'DS_CHECKNEWHOME',
  ACTION_DRAFTSET_UPDATEELEMENT: 'DS_UPDATEELEMENT',
  ACTION_DRAFTSET_DELETEELEMENT: 'DS_DELETEELEMENT',
  ACTION_DRAFTSET_PUTCALCULATION: 'DS_PUTCALCULATION',
  ACTION_DRAFTSET_ADDCALCULATION: 'DS_ADDCALCULATION',
  ACTION_DRAFTSET_EDITCALCULATION: 'DS_EDITCALCULATION',
  ACTION_DRAFTSET_CLONECALCULATION: 'DS_CLONECALCULATION',
  ACTION_DRAFTSET_UPDATECALCULATION: 'DS_UPDATECALCULATION',
  ACTION_DRAFTSET_DELETECALCULATION: 'DS_DELETECALCULATION',
  ACTION_DRAFTSET_PUBLISH: 'DS_PUBLISH',
  ACTION_DRAFTSET_SAVE: 'DS_SAVE',

  ACTION_DRAFTINSTRUMENTVERSION_CREATESKELETON: 'DIV_CREATESKELETON',
  ACTION_DRAFTINSTRUMENTVERSION_CLONE: 'DIV_CLONE',
  ACTION_DRAFTINSTRUMENTVERSION_PUBLISH: 'DIV_PUBLISH',
  ACTION_DRAFTINSTRUMENTVERSION_DELETE: 'DIV_DELETE',

  RE_DATE: /^[0-9]{4}-[0-9]{2}-[0-9]{2}$/,
  RE_DATETIME: /^([0-9]{4}-[0-9]{2}-[0-9]{2})[ T]?((?:(?:[0-1]?[0-9])|(?:[2][0-3])):(?:[0-5][0-9])(?::(?:[0-5][0-9]))?)?$/,
  RE_FIELD_ID: /^[a-z](?:[a-z0-9]|[_](?![_]))*[a-z0-9]$/,
  RE_ROW_ID: /^[a-z](?:[a-z0-9]|[_](?![_]))*[a-z0-9]$/,
  RE_ENUMERATION_ID: /^(?:[a-z0-9]{1,2}|[a-z0-9](?:[a-z0-9]|[_-](?![_-]))+[a-z0-9])$/,
  RE_PARAMETER_ID: /^[a-z](?:[a-z0-9]|[_](?![_]))*[a-z0-9]$/,
  RE_HOTKEY: /^[0-9]$/
};


module.exports = Constants;
