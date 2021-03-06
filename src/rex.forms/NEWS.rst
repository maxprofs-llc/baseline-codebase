********************
REX.FORMS Change Log
********************

.. contents:: Table of Contents


2.5.0
=====

* Added feedback to the bottom of the page that explains why the user cannot
  currently progress to the next page (e.g., errors, missing required fields,
  etc).
* Slight styling updates to required fields.


2.4.3 (2018-06-25)
==================

* Fixed an issue where the ``forms_presentation_adaptors`` setting wasn't
  merging values in a useful way.
* Fixed some rendering issues with respect to enumeration choices and hotkey
  information.


2.4.2 (2018-05-14)
==================

* Adjusted width of text widgets to be full-width on narrow screens (mobile
  devices, etc).
* Fixed issues with the behavior of date/time fields on Android.


2.4.1 (2017-11-10)
==================

* Fixed an issue that caused long text being not wrapped on reconciliation
  screens.

2.4.0 (2017-09-15)
==================

* Fixed an issue that caused weird behavior when the first page of a form is
  hidden immediately.
* Added an ability to the JavaScript component API to allow the use of custom
  widgets.


2.3.2 (2017-06-20)
==================

* Fixed a wordwrap issue with displaying long values in the reconciler.
* Now handles reconciliation scenarios where a recordList record must have a
  value chosen in the solution.


2.3.1 (2017-02-07)
==================

* Fixed an issue that caused the review/readonly views to show zeros in
  integer and float fields as "No Value".


2.3.0 (2017-01-19)
==================

* JS dependency updates.


2.2.0 (2016-10-25)
==================

* The ``FormError`` exception now inherits from ``rex.core.Error``.
* The ability to generate Form skeletons based on Instrument Definitions is
  now exposed via the ``make_form_skeleton()`` function.
* Fixed an issue that caused Forms to not render if their configuration
  contains invalid REXL expressions.
* Fixed an issue that caused enumerationSet choices to be crammed together
  when displayed in Review mode.


2.1.0 (2016-09-14)
==================

* Fixed issue with the form not auto-focusing the next field when a hotkey is
  used to select the same value that is already selected.
* Refactored the calculation preview APIs for more reusability.
* Adjusted calculation preview popup to handle configurations with lots of
  calculations.
* Fixed issues with date/dateTime validation in some browsers.


2.0.0 (2016-08-12)
==================

* Completely overhauled the React components for working with Forms and
  Reconciliations.
* Updated to the new rex.i18n.


1.6.0 (2016-07-14)
==================

* Fixed issue with display of non-text/non-numeric calculations results.
* Updated rios.core dependency.


1.5.0 (2016-04-22)
==================

* The instrument-formskeleton task now sorts the lists of enumerations by their
  ID.
* The instrument-formskeleton task now automatically assigns hotkeys to
  enumerations if all the enumerations in the list have IDs of 0-9.
* Added a new ``lookupText`` widget that can show a list of suggested values
  based on what the user has entered into the text box.
* Added an optional feature to Form entry that allows the user to see a preview
  of what the CalculationSet results would be based on the current state of the
  Form.
* Pressing tab while on the last Question of a Page will now place focus on the
  "Next Page" button, if it exists.
* Fixed issues where constraints (required, length, etc) weren't being enforced
  for recordList questions.
* Fixed an issue that prevented the Annotation field for recordList questions
  from not being presented.


1.4.1 (2016-03-30)
==================

* Updated documentation in support of rex.platform LTS release.


1.4.0 (2016-02-29)
==================

* Added question position information to the reconciliation component to help
  users identify which question on the original Form has the discrepancy.
* Page navigation bar now shows the actual page numbers instead of always
  numbering sequentially from 1.
* Fixed more issues that prevented entering decimal numbers in float fields
  where multiple validation events/contraints are in play.


1.3.0 (2016-01-29)
==================

* Fixed issue that caused auto-tabbing to focus disabled or hidden fields.
* Updated rios.core dependency.
* The locale metadata property is now set on Assessments.


1.2.1 (2015-12-01)
==================

* Fixed issue that prevented entering decimal numbers in float fields that have
  fail events being triggered.


1.2.0 (2015-11-20)
==================

* Adjusted <<Parameter>>'s handling of null values to follow specification.
* Updated rex.ctl tasks to use log() function instead of print statements.
* Updated rios.core dependency.


1.1.0 (2015-10-21)
==================

* Updated all references of PRISMH to RIOS (including changing the dependency
  to rios.core).


1.0.0 (2015-09-30)
==================

- Finally, a major release!
- Added support for the ``orientation`` options on checkGroup/radioGroup
  widgets.
- Added support for the ``autoHotkeys`` and ``hotkeys`` options on the
  checkGroup/radioGroup widgets.
- Fixed some issues with the display of matrix columns and question text.
- Added a PresentationAdaptor extension and ``forms_presentation_adaptors``
  setting that allow you to apply automatic transformations to Form
  Configurations on a per-channel basis.
- Updated prismh.core dependency.
- Added a ``get_implementation()`` method to all Interface classes as a
  convenience wrapper around the same function in the utils module.
- The Form.get_for_task() method now accepts Task instances and Task UIDs.
- Fixed an issue preventing matrix subfields from being event targets.
- Fixed issue with disabled matrix subfields being excluded from the resulting
  Assessment.

Deprecations
------------
The ``entryCheckGroup`` and ``entryRadioGroup`` widgets have been deprecated.
To achieve the same behavior, you can use the normal ``checkGroup`` and
``radioGroup`` widgets and specify either the ``autoHotkeys`` or ``hotkeys``
options.


0.31.0 (2015-06-23)
===================

- Added ability to pass implementation-specific parameters to the ``create()``
  and ``save()`` methods of Form and DraftForm. This is done via the
  ``implementation_context`` dictionary argument.
- Interface classes that accept the ``implementation_context`` argument also
  have a ``get_implementation_context()`` method that describes the extra
  variables that are allowed.
- Fixed issue where values such as "1.0" could not be entered into float
  fields.
- The ``forms-store`` task now accepts a ``--context`` option in order to
  provide implementation context parameters.
- Added compatibility with ``rex.setup`` v3.


0.30.2 (2015-06-26)
===================

- Updated prismh.core dependency.


0.30.1 (2015-06-17)
===================

- Updated instrument dependency.
- Added some caching to event handling in the JS framework, so Forms with large
  or many expressions should be a bit more performant now.


0.30.0 (2015-06-12)
===================

- Moved the Channel, Task, Entry, TaskCompletionProcessor, and
  ParameterSupplier interface classes to the ``rex.instrument`` package.
- Removed the ``forms_default_required_entries`` setting.
- Now using the ``prismh.core`` library for all configuration validation and
  output logic.
- Added a get_for_task() method to Form.
- Fixed some issues with the audio player JavaScript component that would cause
  errors when it was unmounted before expected.

Upgrade Notes
-------------

The Channel, Task, and Entry interface classes were moved to the
``rex.instrument`` package. This means:

  * You'll need to update any import statements that refer to these classes.
  * When using the ``get_implementation()`` function, you no longer have to
    specify ``forms`` as the package argument for these classes.
  * Any place you used the ``forms_implementation`` setting in reference to
    these classes, you'll need to update it to ``instrument_implementation``.

The TaskCompletionProcessor and ParameterSupplier extensions were moved to
the ``rex.instrument`` package. Be sure to update any related import
statements.

The setting ``forms_default_required_entries`` no longer exists. It is now
handled by the ``instrument_default_required_entries`` setting provided by
the ``rex.instrument`` package.

Identifier strings referenced in the Form Configurations can no longer
contain underscore characters.


0.29.1 (2015-05-06)
===================

- Added Spanish translations.


0.29.0 (2015-05-05)
===================

- Added common/default implementations of:

  - Task.can_enter_data
  - Task.can_reconcile
  - Task.start_entry()
  - Task.get_entries()
  - Task.complete_entry()
  - Task.reconcile()

- All find() methods now default to a limit of ``None``, which means no limit.
- The Task.assessment property is now writable.
- Fixed issue in JS components so that when the form configuration changes, it
  resets to the first page.


0.28.2 (2015-04-06)
===================

- Fixed subtitle not being displayed on overview screen.
- Demo application can now read both JSON and YAML configuration files.


0.28.1 (2015-03-26)
===================

- Publishing a DraftForm now automatically sets the instrument ID/Version
  embedded in the configuration to match the InstrumentVersion the DraftForm
  was published against.
- Fixed signature of ``DraftForm.create()`` to make configuration an optional
  kwarg.
- Fixed some issues with the outputting/formatting of configurations with
  non-ASCII characters.


0.28.0 (2015-02-20)
===================

- Updated ``instrument-formskeleton`` task to handle situations where
  enumeration definitions have null values in an Instrument Definition.
- When clicking the player controls on audio clips for enumerations, it will
  no longer select that enumeration.
- The system will now automatically validate all Form configurations found in
  the datastore upon server startup. This can be disabled through a new
  setting named ``forms_validate_on_startup``.
- Added support for the loosened format of Enumeration IDs.
- Added a new setting named ``forms_local_resource_prefix`` that can be used
  to prepend a string to the resource URLs referenced in Form configurations
  (such as Audio files). This value of this setting must be passed to the
  localResourcePrefix prop of the Form JS component.


0.27.0 (2015-01-30)
===================

- Added an optional ``facilitator`` property to the Task interface class.
- Added the ability to play audio files in the form by:

  - Added a new page element of type ``audio`` to allow the insertion of an
    audio file player at any position in the page.
  - Added a new ``audio`` property to Question element options, as well as
    enumeration and matrix row descriptors, which will show audio file players
    with the text of these objects.

- Added support for ``rex.setup`` v2.
- Refactored how the demo/test package works.
- The Task interface class no longer has a ``start()`` method.
- Implementations of the ``find()`` method on Tasks must now accept an
  ``asssessment`` search criteria.
- Fixed an issue where fields with textArea widgets weren't being disabled
  appropriately.
- Now using v2 of ``rex.ctl``.
- The ``forms-validate`` and ``forms-store`` commands will now accept
  YAML-formatted Form and Instrument files, provided they adhere to the same
  structural requirements as the specifications.
- The ``start_entry()`` method on Tasks now accepts an optional ``ordinal``
  argument.
- The ``find()`` and ``create()`` method on Entry now accepts an optional
  ``ordinal`` argument.
- The progress bar now only shows on the screen if there is more than one page
  in the Form.
- Added an ``output`` module with function and classes that can be used to
  output Form configurations in a human-friendly way, with either JSON or
  YAML.
- Added a ``forms-format`` rex command to convert and/or reformat Form
  configurations.
- The ``forms-retrieve`` rex command now accepts a ``format`` option to
  indicate that you want JSON or YAML returned.
- Added a ``configuration_yaml`` property to the Form and DraftForm classes to
  get or set the Form configuration using YAML.
- Added an ``instrument-formskeleton`` rex command that will generate a very
  basic Form configuration based on a specified Instrument definition.


0.26.0 (11/21/2014)
===================

- Integer values are now automatically bounded between -2147483648 and
  +2147483647 to provide better compatibility with downstream applications.
- Fixed issue where some browsers would sort the discrepancies on the
  reconciliation screen in odd ways when the form contains unprompted fields.
- "Complete Reconciliation" button is now disabled when the screen is first
  loaded, and becomes enabled when all discrepancies are addressed -- instead
  of the prior behavior of being hidden until all discrepancies are addressed.
- Client implementations can now pass a subtitle to display under the main
  title.
- Question error text now allows Creole markup.
- Text properties that allow Creole markup now also support Parameter
  substitution using the <<Parameter name>> macro.
- The "Manual Override" option on the reconciliation screen now highlights in
  the same manner as selecting a value from one of the Entries.
- The entryRadioGroup and entryCheckGroup widgets now accept a ``hotkeys``
  option that allows the custom configuration of the hotkeys to assign the
  enumerations in the widget.
- When switching Pages in a Form, the first Question on the Page is now
  automatically put into focus.
- The Entry interface class now has an ``ordinal`` property that contains the
  Entry's ordinal position in the collection of Entries associated with the
  Task.
- Implementations of the Task.find() method must now allow a list of statuses
  to match on.
- Removed the VALIDATING status from Tasks.
- Added a property named ``num_required_entries`` to the Task class that allows
  implementations to indicate how many Entries must be created and reconciled
  in order to complete the Task.
- Added a setting named ``forms_default_required_entries`` which gives the
  system a default value to use if a Task doesn't specify a value for its
  ``num_required_entries`` property.
- Added a property named ``can_enter_data`` to the Task class that allows
  implementations to provide an indicator for whether or not the Task is in a
  state that allows the creation of new Preliminary Entries.
- The ``can_reconcile`` property on the Task class is now abstract and must be
  implemented by concrete classes.
- Fixed issues where defaulted dates were timezone-naive, and thus causing
  confusing shifts in date/time.


0.25.1 (10/17/2014)
===================

- Fixed issue that caused crashes when tags were assigned to Questions.


0.25.0 (10/13/2014)
===================

- Added/Fixed the ability to target pages and element tag groups in events.
- Fixed an issue when trying to view Forms w/ Assessments that had matrix
  values set to null.
- Fixed an issue that caused the read-only view of form data to crash if the
  selected enumeration had hideEnumeration events associated with it.
- Fixed an issue where disabling recordList or matrix fields only partially
  did so.
- Loosened up text-based fields so that they can accept calculations that
  result in numeric values.
- Added enumeration-based widgets that support keyboard hotkeys.
- Fixed a crash that occurred when trying to reconcile matrix fields that are
  null.
- Fixed an issue where under certain circumstances the reconciler would get
  confused of the status of recordList/matrix sub-fields that had validations
  on them.
- Fixed issue where the Remove button for records in a recordList question
  would appear to be disabled if the first question in the recod is disabled.


0.24.0 (10/2/2014)
==================

- Added ability to reference enumerationSet fields in REXL expressions to
  receive a List of the selected enumerations.
- Added ability to reference recordList sub-fields in REXL expressions to
  receive a List of that field's values across the records in the recordList.
- Added ability to target ``hide``, ``disable``, and ``hideEnumeration``
  actions at the subfields within recordList and matrix questions.


0.23.0 (9/26/2014)
==================

- The JavaScript components are now using the RexI18N framework for
  localization.
- Fixed issues with referencing enumerationSet enumerations and matrix
  sub-fields in REXL expressions.
- Fixed some issues with REXL identifier resolution not returning correct data
  type.
- The radioGroup widget now includes the ability for users to clear out their
  selection.
- The progress bar is now measured as the current page over the total number of
  pages.
- Fixed the issue that prevented multiple events targetting the same field.
- The discrepancies listed on the Reconciliation screen are now in the same
  order as the fields appear in the original Form.
- Added text to screen to explain why the Next Page button is disabled.
- The "Complete Form" button now says "Review Responses" when in entry mode,
  and "Complete Form" when in review mode.
- Fixed issue of not being able to disable checkGroup, dropDown, or radioGroup
  widgets.
- The reconciliation screen now requires the user to explictly address each
  discrepancy listed, whether they choose an entered value or manually
  override the value. The "complete" button will now not appear until all
  discrepancies have been dealt with.
- The display of multi-line text on the review/read-only screen now actually
  shows the linebreaks instead of one continue string of text.


0.22.2 (9/17/2014)
==================

- Fixed a problem where the JS component would generate an Assessment document
  with parially-complete recordList records.
- Fixed a crash when finding discrepancies with enumerationSet fields.
- Fixed issues with displaying discrepancies for enumerationSet fields and
  fields using custom types.
- Fixed the enumeration/enumerationSet widgets displaying Yes/No as choices
  when the enumeration text for the question wasn't defined in the Form config.
- Fixed an issue where decimal numbers were being silently accepted and
  truncated when entered in integer fields.
- Fixed an issue where values with extra, non-numeric characters were being
  silently accepted and dropped in some situations when interacting with
  integer and float fields.
- When entering the "review" phase of completing a Form, the page will now
  scroll to the top of the Form.
- Fixed issues when solving discrepancies involving recordList and matrix
  fields that caused invalid Assessments to be generated.
- When tabbing through a Form, when an dropDown or radioGroup widget is
  encountered, the full list of choices is scrolled into view.
- Fixed issues with enumeration fields embedded within recordList and matrix
  fields not allowing more than one selection across all instances of that
  field.
- Required fields are now marked as such on the reconciliation screen.
- If the final value on the reconciliation screen is modified by hand, the
  previously-selected value is dehighlighted.
- Required rows in matrix fields are now flagged as such.
- Fixed an issue in reconciliation screen where it didn't reliably detect if
  all required values were entered.
- Fixed an issue that prevented the solving of discrepancies including an
  empty enumerationSet value.
- The output from the forms-retrieve command can now be optionally
  pretty-printed.


0.22.1 (9/3/2014)
=================

- Fixed an issue where the reconciler JS component would crash if it
  encountered a null value.


0.22.0 (8/25/2014)
==================

- Changed Form.validate_configuration() parameter naming to align to that used
  in the Assessment.validate_data() method.
- Addressed changes to the Assessment.validate_data() interface method.
- All get_by_uid() and find() methods now accept and optional user parameter to
  indicate that the resulting instance should be accessible by the specified
  User.
- Fixed rendering of boolean fields as dropDown widgets.
- Default date/time/dateTime fields are no longer gigantic.
- Fixed an issue where matrix questions couldn't define their rows.
- It's now possible to cancel the input of an optional explanation/annotation.
- Invalid JSON is now considered a ValidationError by
  Form.validate_configuration().
- The forms-validate command now takes an option to specify the Instrument JSON
  to validate against.
- Fixed an issue where the target property on an Event Object wasn't being
  treated as an array.
- The target property on an Event Object in a Form Configuration has been
  renamed to "targets".
- Fixed an issue where the hideEnumeration action was hiding objects listed in
  the "targets" property rather than the "enumerations" option.
- Fixed an issue where the calculation action was performing calculations based
  on the expression in the "targets" property rather than the "calculation"
  option.
- Added support for calculating the values of unprompted fields.
- The fail action now takes the error message to display from the "text"
  option.
- Fixed issue of enumeration, enumerationSet, and boolean fields not displaying
  the proper text for the selected choices on the review screen.
- Added ability to configure the labels of the buttons on the recordList
  widget.


0.21.0 (7/31/2014)
==================

- Added an extension called TaskCompletionProcessor to allow custom logic to
  be executed after a Task has been completed.
- Updated the Entry.validate_data() method to support the updated validation
  logic provided by Assessment.validate_data().
- Entry data is now only validated upon complete, rather than on
  instantiation and assignment.
- Form will no longer validation the configuration upon instantiation or
  assignment.
- Fixed issue with enumerations not showing.
- Updated references to Instrument.get_latest_version() to new property.
- Most sub-object properties now perform lazy retrieval with caching.
- Added new interface class in DraftForm to allow the management of Forms that
  are in the process of being created and aren't ready for general use in the
  system.


0.20.0 (6/30/2014)
==================

- Added JS component for facilitating Entry reconciliations.
- Fixed issue with discrepancy solving API not recognizing overrides of
  ``None``.
- Upgraded react-forms.


0.19.1-2 (6/24/2014)
====================

- Packaging fixes.


0.19.0 (6/24/2014)
==================

- Added a series of interface and utility classess, to mirror and function with
  those defined in ``rex.instrument``.
- Changed structure of Form JSON representation.
- Complete rewrite of form rendering library.


0.11.2 (6/17/2014)
==================

- Tightened the version bounds on rex.expression.


0.11.1 (6/2/2014)
=================

- Changed how the REXL/rex.expression library was referenced.


0.11.0
======

- Added support for slider widgets.


0.10.4
======

- Documentation updates in preparation for open-sourcing.


0.2.2
=====

- syncronization of versions in setup.py and in repository

0.2.1
=====

- fixed RELEASE-NOTES.rst

0.2.0
=====

- basic tests
- value validation by domains
- changed rendering of annotations and explanations
- more friendly preview mode

