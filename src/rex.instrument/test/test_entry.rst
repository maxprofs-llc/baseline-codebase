*****
Entry
*****


Set up the environment::

    >>> from rex.core import Rex
    >>> rex = Rex('__main__', 'rex.demo.instrument')
    >>> rex.on()


The semi-abstract base Task class only implements a simple constructor
and string-rendering methods::

    >>> from rex.instrument.interface import User, Subject, Instrument, InstrumentVersion, Assessment, Entry
    >>> from datetime import datetime
    >>> subject = Subject('fake123')
    >>> instrument = Instrument('fake123', 'fake123', 'My Instrument Title')
    >>> INSTRUMENT = {
    ...     'id': 'urn:test-instrument',
    ...     'version': '1.1',
    ...     'title': 'The InstrumentVersion Title',
    ...     'record': [
    ...         {
    ...             'id': 'q_fake',
    ...             'type': 'text'
    ...         }
    ...     ]
    ... }
    >>> iv = InstrumentVersion('notreal456', instrument, INSTRUMENT, 1, 'jay', datetime(2014, 5, 22))
    >>> ASSESSMENT = {
    ...     'instrument': {
    ...         'id': 'urn:test-instrument',
    ...         'version': '1.1'
    ...     },
    ...     'values': {
    ...         'q_fake': {
    ...             'value': 'my answer'
    ...         }
    ...     }
    ... }
    >>> assessment = Assessment('fake123', subject, iv, ASSESSMENT)

    >>> entry = Entry('entry333', assessment, Entry.TYPE_PRELIMINARY, ASSESSMENT, 'bob', datetime(2014, 5, 22, 12, 34, 56), 1, memo='hi mom')
    >>> entry.get_display_name()
    'entry333'
    >>> str(entry)
    'entry333'
    >>> str(entry)
    'entry333'
    >>> repr(entry)
    "Entry('entry333', Assessment('fake123', Subject('fake123'), InstrumentVersion('notreal456', Instrument('fake123', 'My Instrument Title'), 1)), 'preliminary')"
    >>> entry.created_by
    'bob'
    >>> entry.date_created
    datetime.datetime(2014, 5, 22, 12, 34, 56)
    >>> entry.modified_by
    'bob'
    >>> entry.date_modified
    datetime.datetime(2014, 5, 22, 12, 34, 56)
    >>> entry.memo
    'hi mom'

    >>> entry.as_dict()
    {'uid': 'entry333', 'ordinal': 1, 'status': 'in-progress', 'type': 'preliminary', 'created_by': 'bob', 'date_created': datetime.datetime(2014, 5, 22, 12, 34, 56), 'modified_by': 'bob', 'date_modified': datetime.datetime(2014, 5, 22, 12, 34, 56)}
    >>> entry.as_json()
    '{"uid": "entry333", "ordinal": 1, "status": "in-progress", "type": "preliminary", "created_by": "bob", "date_created": "2014-05-22T12:34:56", "modified_by": "bob", "date_modified": "2014-05-22T12:34:56"}'


The Assessments passed to the constructor must actually be an instance of that
class or a string containing a UID::

    >>> entry = Entry('entry333', object(), Entry.TYPE_PRELIMINARY, ASSESSMENT, 'bob', datetime(2014, 5, 22, 12, 34, 56), 1, memo='hi mom')
    Traceback (most recent call last):
      ...
    ValueError: assessment must be an instance of Assessment or a UID of one

    >>> entry = Entry('entry333', 'assessment1', Entry.TYPE_PRELIMINARY, ASSESSMENT, 'bob', datetime(2014, 5, 22, 12, 34, 56), 1, memo='hi mom')
    >>> entry.assessment
    DemoAssessment('assessment1', DemoSubject('subject1'), DemoInstrumentVersion('simple1', DemoInstrument('simple', 'Simple Instrument'), 1))


The data can be passed to the contructor as either a JSON-encoded string
or the dict equivalent::

    >>> entry = Entry('entry333', assessment, Entry.TYPE_PRELIMINARY, '{"instrument": {"id": "urn:test-instrument", "version": "1.1"}, "values": {"q_fake": {"value": "my answer"}}}', 'bob', datetime(2014, 5, 22, 12, 34, 56), 1, memo='hi mom')
    >>> entry.validate()


The data can be set or retrieved as either a JSON-encoded string or a dict
equivalent::

    >>> entry.data
    {'instrument': {'id': 'urn:test-instrument', 'version': '1.1'}, 'values': {'q_fake': {'value': 'my answer'}}}
    >>> entry.data = {'instrument': {'version': '1.1', 'id': 'urn:test-instrument'}, 'values': {'q_fake': {'value': 'my different answer'}}}

    >>> entry.data_json
    '{"instrument": {"version": "1.1", "id": "urn:test-instrument"}, "values": {"q_fake": {"value": "my different answer"}}}'
    >>> entry.data_json = '{"instrument": {"version": "1.1", "id": "urn:test-instrument"}, "values": {"q_fake": {"value": "something completely different"}}}'


Entries have date_modified, modified_by, status, and memo properties which are
both readable and writable::

    >>> entry = Entry('entry333', assessment, Entry.TYPE_PRELIMINARY, ASSESSMENT, 'bob', datetime(2014, 5, 22, 12, 34, 56), 1, memo='hi mom')

    >>> entry.date_modified
    datetime.datetime(2014, 5, 22, 12, 34, 56)
    >>> entry.date_modified = datetime(2014, 6, 1)
    >>> entry.date_modified
    datetime.datetime(2014, 6, 1, 0, 0)
    >>> entry.date_modified = '20140602'
    Traceback (most recent call last):
        ...
    ValueError: "20140602" is not a valid datetime
    >>> entry.date_modified
    datetime.datetime(2014, 6, 1, 0, 0)

    >>> entry.modified_by
    'bob'
    >>> entry.modified_by = 'jay'
    >>> entry.modified_by
    'jay'

    >>> entry.status
    'in-progress'
    >>> entry.is_done
    False
    >>> entry.status = Entry.STATUS_COMPLETE
    >>> entry.status
    'complete'
    >>> entry.is_done
    True
    >>> entry.status = 'something else'
    Traceback (most recent call last):
        ...
    ValueError: "something else" is not a valid Entry status
    >>> entry.status
    'complete'

    >>> entry.memo
    'hi mom'
    >>> entry.memo = 'A long time ago in a galaxy far, far away...'
    >>> entry.memo
    'A long time ago in a galaxy far, far away...'


Entries have a ``complete()`` method that performs some end-of-data-collection
tasks on the Entry and its Assessment Data::

    >>> user = User('fakeuser', 'fakelogin')
    >>> entry = Entry('entry333', assessment, Entry.TYPE_PRELIMINARY, ASSESSMENT, 'bob', datetime(2014, 5, 22, 12, 34, 56), 1, memo='hi mom')

    >>> entry.status
    'in-progress'
    >>> entry.get_meta('application') is None
    True
    >>> entry.get_meta('dateCompleted') is None
    True
    >>> entry.complete(user)
    >>> entry.status
    'complete'
    >>> 'rex.instrument' in entry.get_meta('application')
    True
    >>> entry.get_meta('dateCompleted') is None
    False

    >>> entry.complete(user)
    Traceback (most recent call last):
        ...
    rex.instrument.errors.InstrumentError: Cannot complete an Entry that is already in a terminal state.


Entries have some convenience methods for setting and retrieving metadata
properties on the Assessment Document::

    >>> entry = Entry('entry333', assessment, Entry.TYPE_PRELIMINARY, ASSESSMENT, 'bob', datetime(2014, 5, 22, 12, 34, 56), 1, memo='hi mom')

    >>> entry.get_meta('foo') is None
    True
    >>> entry.set_meta('foo', 'bar')
    >>> entry.get_meta('foo')
    'bar'

    >>> entry.get_meta('application') is None
    True
    >>> entry.set_application_token('coolapp', '1.0')
    'coolapp/1.0'
    >>> entry.set_application_token('helper')
    'coolapp/1.0 helper/?'
    >>> entry.set_application_token('coolapp', '2.0')
    'coolapp/2.0 helper/?'
    >>> entry.get_meta('application')
    'coolapp/2.0 helper/?'


There's a static method on Entry named `generate_empty_data()` that will
create an Assessment Document that contains no response data, but is in the
structure expected for the specified InstrumentVersion::

    >>> Entry.generate_empty_data(iv)
    {'instrument': {'id': 'urn:test-instrument', 'version': '1.1'}, 'values': {'q_fake': {'value': None}}}
    >>> Entry.validate_data(Entry.generate_empty_data(iv))


Entry can be checked for equality. Note that equality is only defined as
being the same class with the same UID::

    >>> entry1 = Entry('entry333', assessment, Entry.TYPE_PRELIMINARY, ASSESSMENT, 'bob', datetime(2014, 5, 22, 12, 34, 56), 1, memo='hi mom')
    >>> entry2 = Entry('entry444', assessment, Entry.TYPE_PRELIMINARY, ASSESSMENT, 'bob', datetime(2014, 5, 22, 12, 34, 56), 2, memo='hi mom')
    >>> entry3 = Entry('entry333', assessment, Entry.TYPE_RECONCILED, ASSESSMENT, 'bob', datetime(2014, 5, 22, 12, 34, 56), 3, memo='hi mom')
    >>> entry1 == entry2
    False
    >>> entry1 == entry3
    True
    >>> entry1 != entry2
    True
    >>> entry1 != entry3
    False
    >>> mylist = [entry1]
    >>> entry1 in mylist
    True
    >>> entry2 in mylist
    False
    >>> entry3 in mylist
    True
    >>> myset = set(mylist)
    >>> entry1 in myset
    True
    >>> entry2 in myset
    False
    >>> entry3 in myset
    True

    >>> entry1 < entry2
    True
    >>> entry1 <= entry3
    True
    >>> entry2 > entry1
    True
    >>> entry3 >= entry1
    True


