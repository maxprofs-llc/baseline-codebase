#
# Copyright (c) 2014, Prometheus Research, LLC
#


import sys

from prismh.core.validation.instrument import TYPES_ALL
from rex.core import Error, AnyVal
from rex.ctl import Task, RexTask, argument, option
from rex.instrument import InstrumentVersion
from rex.instrument.ctl import \
    open_and_validate as open_and_validate_instrument, \
    ImplementationContextReceiver
from rex.instrument.util import get_implementation

from .errors import ValidationError
from .interface import Form
from .output import dump_form_yaml, dump_form_json


__all__ = (
    'FormsValidateTask',
    'FormsFormatTask',
    'FormsRetrieveTask',
    'FormsStoreTask',
    'InstrumentFormSkeleton',
)


# pylint: disable=E1101,C0103


def open_and_validate(
        filename,
        instrument_definition=None,
        instrument_file=None):
    try:
        configuration = open(filename, 'r').read()
    except Exception as exc:
        raise Error('Could not open "%s": %s' % (
            filename,
            str(exc),
        ))

    if (not instrument_definition) and instrument_file:
        try:
            instrument_definition = AnyVal().parse(
                open(instrument_file, 'r').read()
            )
        except Exception as exc:
            raise Error('Could not open "%s": %s' % (
                instrument_file,
                str(exc),
            ))

    try:
        configuration = AnyVal().parse(configuration)
        Form.validate_configuration(
            configuration,
            instrument_definition=instrument_definition,
        )
    except ValidationError as exc:
        raise Error(exc.message)

    return configuration


class FormsValidateTask(Task):
    """
    validate a Web Form Configuration

    The forms-validate task will validate the structure and content of the Web
    Form Configuration in a file and report back if any errors are found.

    The configuration is the path to the file containing the Web Form
    Configuration to validate.
    """

    name = 'forms-validate'

    class arguments(object):  # noqa
        configuration = argument(str)

    class options(object):  # noqa
        instrument = option(
            None,
            str,
            default=None,
            value_name='FILE',
            hint='the file containing the associated Instrument Definition;'
            ' if not specified, then the Web Form Configuration will only be'
            ' checked for schema violations',
        )

    def __call__(self):
        open_and_validate(
            self.configuration,
            instrument_file=self.instrument,
        )

        print '"%s" contains a valid Web Form Configuration.\n' % (
            self.configuration,
        )


def output_forms(val):
    val = val.upper()
    if val in ('JSON', 'YAML'):
        return val
    raise ValueError('Invalid format type "%s" specified' % val)


class FormOutputter(object):
    class options(object):  # noqa
        output = option(
            None,
            str,
            default=None,
            value_name='OUTPUT_FILE',
            hint='the file to write to; if not specified, stdout is used',
        )
        format = option(
            None,
            output_forms,
            default='JSON',
            value_name='FORMAT',
            hint='the format to output the configuration in; can be either'
            ' JSON or YAML; if not specified, defaults to JSON',
        )
        pretty = option(
            None,
            bool,
            hint='if specified, the outputted configuration will be formatted'
            ' with newlines and indentation',
        )

    def do_output(self, structure):
        if self.output:
            try:
                output = open(self.output, 'w')
            except Exception as exc:
                raise Error('Could not open "%s" for writing: %s' % (
                    self.output,
                    str(exc),
                ))
        else:
            output = sys.stdout

        if self.format == 'JSON':
            output.write(
                dump_form_json(
                    structure,
                    pretty=self.pretty,
                )
            )
        elif self.format == 'YAML':
            output.write(
                dump_form_yaml(
                    structure,
                    pretty=self.pretty,
                )
            )

        output.write('\n')


class FormsFormatTask(Task, FormOutputter):
    """
    render a Web Form Configuration into various formats

    The forms-format task will take an input Web Form Configuration file and
    output it as either JSON or YAML.

    The configuration is the path to the file containing the Web Form
    Configuration to format.
    """

    name = 'forms-format'

    class arguments(object):  # noqa
        configuration = argument(str)

    def __call__(self):
        configuration = open_and_validate(self.configuration)
        self.do_output(configuration)


class FormsRetrieveTask(RexTask, FormOutputter):
    """
    retrieves a Form from the datastore

    The forms-retrieve task will retrieve a Form from a project's data store
    and return the Web Form Configuration.

    The instrument-uid argument is the UID of the desired Instrument in the
    data store.

    The channel-uid argument is the UID of the Channel that the Form is
    assigned to.
    """

    name = 'forms-retrieve'

    class arguments(object):  # noqa
        instrument_uid = argument(str)
        channel_uid = argument(str)

    class options(object):  # noqa
        version = option(
            None,
            str,
            default=None,
            value_name='VERSION',
            hint='the version of the Instrument to retrieve; if not specified,'
            ' defaults to the latest version',
        )

    def __call__(self):
        with self.make():
            instrument_impl = get_implementation('instrument')
            instrument = instrument_impl.get_by_uid(self.instrument_uid)
            if not instrument:
                raise Error('Instrument "%s" does not exist.' % (
                    self.instrument_uid,
                ))

            if not self.version:
                instrument_version = instrument.latest_version
            else:
                instrument_version = instrument.get_version(self.version)
            if not instrument_version:
                raise Error('The desired version of "%s" does not exist.' % (
                    self.instrument_uid,
                ))

            channel_impl = get_implementation('channel')
            channel = channel_impl.get_by_uid(self.channel_uid)
            if not channel:
                raise Error('Channel "%s" does not exist.' % (
                    self.channel_uid,
                ))
            if channel.presentation_type != channel_impl.PRESENTATION_TYPE_FORM:
                raise Error('Channel "%s" is not a web form channel.' % (
                    channel.uid,
                ))

            form_impl = get_implementation('form', package_name='forms')
            form = form_impl.find(
                instrument_version=instrument_version,
                channel=channel,
                limit=1
            )
            if form:
                form = form[0]
            else:
                raise Error(
                    'No Form exists for Instrument "%s", Version %s,'
                    ' Channel "%s"' % (
                        instrument.uid,
                        instrument_version.version,
                        channel.uid,
                    )
                )

            self.do_output(form.configuration)


class FormsStoreTask(RexTask, ImplementationContextReceiver):
    """
    stores a Form in the data store

    The forms-store task will write a Web Form Configuration file to a Form in
    the project's data store.

    The instrument-uid argument is the UID of the desired Instrument that the
    Form will be associated with.

    The channel-uid argument is the UID of the Channel that the Form will be
    associated with.

    The configuration is the path to the file containing the Web Form
    Configuration to use.
    """

    name = 'forms-store'

    class arguments(object):  # noqa
        instrument_uid = argument(str)
        channel_uid = argument(str)
        configuration = argument(str)

    class options(object):  # noqa
        version = option(
            None,
            str,
            default=None,
            value_name='VERSION',
            hint='the version of the Instrument to associate the Form with; if'
            ' not specified, then the latest version will be used',
        )

    def __call__(self):
        with self.make():
            instrument_impl = get_implementation('instrument')
            instrument = instrument_impl.get_by_uid(self.instrument_uid)
            if not instrument:
                raise Error('Instrument "%s" does not exist.' % (
                    self.instrument_uid,
                ))
            print 'Using Instrument: %s' % instrument

            if not self.version:
                instrument_version = instrument.latest_version
            else:
                instrument_version = instrument.get_version(self.version)
            if not instrument_version:
                raise Error('The desired version of "%s" does not exist.' % (
                    self.instrument_uid,
                ))
            print 'Instrument Version: %s' % instrument_version.version

            configuration = open_and_validate(
                self.configuration,
                instrument_definition=instrument_version.definition,
            )

            channel_impl = get_implementation('channel')
            channel = channel_impl.get_by_uid(self.channel_uid)
            if not channel:
                raise Error('Channel "%s" does not exist.' % (
                    self.channel_uid,
                ))
            if channel.presentation_type != channel_impl.PRESENTATION_TYPE_FORM:
                raise Error('Channel "%s" is not a web form channel.' % (
                    channel.uid,
                ))
            print 'Using Channel: %s' % channel

            form_impl = get_implementation('form', package_name='forms')
            form = form_impl.find(
                instrument_version=instrument_version,
                channel=channel,
                limit=1
            )
            if form:
                form[0].configuration = configuration
                form[0].save()
                print 'Updated existing Form'
            else:
                form = form_impl.create(
                    channel,
                    instrument_version,
                    configuration,
                    implementation_context=self.get_context(
                        form_impl,
                        form_impl.CONTEXT_ACTION_CREATE,
                    ),
                )
                print 'Created new Form'


class InstrumentFormSkeleton(Task, FormOutputter):
    """
    generate a basic Web Form Configuration from an Instrument Definintion

    The only argument to this task is the filename of the Instrument.
    """

    name = 'instrument-formskeleton'

    class arguments(object):  # noqa
        definition = argument(str)

    class options(object):  # noqa
        localization = option(
            None,
            str,
            default='en',
            value_name='LOCALE',
            hint='the locale to use as the default localization; if not'
            ' specified, defaults to "en"',
        )

    def __call__(self):
        instrument = open_and_validate_instrument(self.definition)

        configuration = self.make_form(instrument)
        try:
            # Double check what we produced to make sure it's valid.
            Form.validate_configuration(configuration, instrument)
        except ValidationError as exc:  # pragma: no cover
            raise Error(
                'Unable to validate form configuration: %s' % exc.message
            )

        self.do_output(configuration)

    def _text(self, text):
        return {
            self.localization: text,
        }

    def make_form(self, instrument):
        form = {}

        form['instrument'] = {
            'id': instrument['id'],
            'version': instrument['version'],
        }

        form['defaultLocalization'] = self.localization

        if 'title' in instrument:
            form['title'] = self._text(instrument['title'])

        page = {
            'id': 'page1',
            'elements': [],
        }

        for field in instrument['record']:
            page['elements'].append({
                'type': 'question',
                'options': self.make_question_options(field, instrument),
            })

        form['pages'] = [page]

        return form

    def make_question_options(self, field, instrument):
        opts = {
            'fieldId': field['id'],
            'text': self._text(field.get('description', field['id'])),
        }

        type_def = InstrumentVersion.get_full_type_definition(
            instrument,
            field['type'],
        )

        if 'enumerations' in type_def:
            opts['enumerations'] = [
                {
                    'id': key,
                    'text': self._text(
                        defn.get('description', key) if defn else key
                    )
                }
                for key, defn in type_def['enumerations'].items()
            ]

        if 'rows' in type_def:
            opts['rows'] = [
                {
                    'id': row['id'],
                    'text': self._text(row.get('description', row['id']))
                }
                for row in type_def['rows']
            ]

        for name in ('record', 'columns'):
            if name in type_def:
                opts['questions'] = [
                    self.make_question_options(subfield, instrument)
                    for subfield in type_def[name]
                ]

        return opts

