*********
DraftForm
*********

.. contents:: Table of Contents


Set up the environment::

    >>> from rex.core import Rex
    >>> from datetime import datetime
    >>> rex = Rex('__main__', 'rex.forms_demo')
    >>> rex.on()


The semi-abstract base DraftForm class only implements a simple constructor
and string-rendering methods::

    >>> from rex.instrument.interface import Instrument, DraftInstrumentVersion
    >>> from datetime import datetime
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
    >>> div = DraftInstrumentVersion('notreal456', instrument, 'jay', datetime(2014, 5, 22), definition=INSTRUMENT)
    >>> from rex.forms.interface import Channel, DraftForm
    >>> channel = Channel('chan135', 'My EDC Application')
    >>> FORM = {
    ...     'instrument': {
    ...         'id': 'urn:test-instrument',
    ...         'version': '1.1',
    ...     },
    ...     'defaultLocalization': 'en',
    ...     'title': {
    ...         'en': 'Our Test Form',
    ...         'fr': u'Ma grande forme'
    ...     },
    ...     'pages': [
    ...         {
    ...             'id': 'page1',
    ...             'elements': [
    ...                 {
    ...                     'type': 'question',
    ...                     'options': {
    ...                         'fieldId': 'q_fake',
    ...                         'text': {
    ...                             'en': 'What is your favorite word?',
    ...                             'fr': u'Quel est votre mot préféré?'
    ...                         },
    ...                     },
    ...                 },
    ...             ],
    ...         },
    ...     ],
    ... }
    >>> df = DraftForm('foo789', channel, div, FORM)
    >>> df.get_display_name()
    u'Our Test Form'
    >>> unicode(df)
    u'Our Test Form'
    >>> str(df)
    'Our Test Form'
    >>> repr(df)
    "DraftForm(u'foo789', Channel(u'chan135', u'My EDC Application'), DraftInstrumentVersion(u'notreal456', Instrument(u'fake123', u'My Instrument Title')))"

    >>> from copy import deepcopy
    >>> FORM_NOTITLE = deepcopy(FORM)
    >>> FORM_NOTITLE['defaultLocalization'] = 'fr'
    >>> df = DraftForm('foo789', channel, div, FORM_NOTITLE)
    >>> df.get_display_name()
    u'Ma grande forme'
    >>> del FORM_NOTITLE['title']
    >>> df = DraftForm('foo789', channel, div, FORM_NOTITLE)
    >>> df.get_display_name()
    u'The InstrumentVersion Title'

    >>> df.as_dict()
    {'draft_instrument_version': {'parent_instrument_version': None, 'modified_by': u'jay', 'uid': u'notreal456', 'date_modified': datetime.datetime(2014, 5, 22, 0, 0), 'created_by': u'jay', 'instrument': {'status': u'active', 'code': u'fake123', 'uid': u'fake123', 'title': u'My Instrument Title'}, 'date_created': datetime.datetime(2014, 5, 22, 0, 0)}, 'uid': u'foo789', 'channel': {'uid': u'chan135', 'title': u'My EDC Application'}}
    >>> df.as_json()
    u'{"draft_instrument_version": {"parent_instrument_version": null, "modified_by": "jay", "uid": "notreal456", "date_modified": "2014-05-22T00:00:00", "created_by": "jay", "instrument": {"status": "active", "code": "fake123", "uid": "fake123", "title": "My Instrument Title"}, "date_created": "2014-05-22T00:00:00"}, "uid": "foo789", "channel": {"uid": "chan135", "title": "My EDC Application"}}'


The Channels and DraftInstrumentVersions passed to the constructor must
actually be instances of those classes or strings containing UIDs::

    >>> df = DraftForm('foo789', object(), div, FORM)
    Traceback (most recent call last):
      ...
    ValueError: channel must be an instance of Channel or a UID of one
    >>> df = DraftForm('foo789', channel, object(), FORM)
    Traceback (most recent call last):
      ...
    ValueError: draft_instrument_version must be an instance of DraftInstrumentVersion or a UID of one

    >>> df = DraftForm('foo789', 'channel1', 'div1', FORM)
    >>> df.channel
    MyChannel(u'channel1', u'Title for channel1')
    >>> df.draft_instrument_version
    MyDraftInstrumentVersion(u'div1', MyInstrument(u'fake_instrument_1iv', u'Title for fake_instrument_1iv'))


The configuration can be passed to the contructor as either a JSON-encoded
string or the dict equivalent::

    >>> import json
    >>> FORM_JSON = json.dumps(FORM)
    >>> FORM_JSON
    '{"instrument": {"version": "1.1", "id": "urn:test-instrument"}, "defaultLocalization": "en", "pages": [{"elements": [{"type": "question", "options": {"text": {"fr": "Quel est votre mot pr\\u00c3\\u00a9f\\u00c3\\u00a9r\\u00c3\\u00a9?", "en": "What is your favorite word?"}, "fieldId": "q_fake"}}], "id": "page1"}], "title": {"fr": "Ma grande forme", "en": "Our Test Form"}}'
    >>> df = DraftForm('foo789', channel, div, FORM_JSON)
    >>> df.validate()


The configuration can be set or retrieved as either a JSON-encoded string or a
dict equivalent::

    >>> df.configuration
    {u'instrument': {u'version': u'1.1', u'id': u'urn:test-instrument'}, u'defaultLocalization': u'en', u'pages': [{u'elements': [{u'type': u'question', u'options': {u'text': {u'fr': u'Quel est votre mot pr\xc3\xa9f\xc3\xa9r\xc3\xa9?', u'en': u'What is your favorite word?'}, u'fieldId': u'q_fake'}}], u'id': u'page1'}], u'title': {u'fr': u'Ma grande forme', u'en': u'Our Test Form'}}
    >>> df.configuration = {u'instrument': {u'version': u'1.1', u'id': u'urn:test-instrument'}, u'defaultLocalization': u'en', u'pages': [{u'elements': [{u'type': u'question', u'options': {u'text': {u'fr': u'Quel est votre mot pr\xc3\xa9f\xc3\xa9r\xc3\xa9?', u'en': u'What is your favorite word?'}, u'fieldId': u'q_fake'}}], u'id': u'page1'}], u'title': {u'fr': u'Ma grande forme', u'en': u'A Different Title'}}

    >>> df.configuration_json
    u'{"instrument": {"version": "1.1", "id": "urn:test-instrument"}, "defaultLocalization": "en", "pages": [{"elements": [{"type": "question", "options": {"text": {"fr": "Quel est votre mot pr\xc3\xa9f\xc3\xa9r\xc3\xa9?", "en": "What is your favorite word?"}, "fieldId": "q_fake"}}], "id": "page1"}], "title": {"fr": "Ma grande forme", "en": "A Different Title"}}'
    >>> df.configuration_json = u'{"instrument": {"version": "1.1", "id": "urn:test-instrument"}, "defaultLocalization": "en", "pages": [{"elements": [{"type": "question", "options": {"text": {"fr": "Quel est votre mot pr\xc3\xa9f\xc3\xa9r\xc3\xa9?", "en": "What is your favorite word?"}, "fieldId": "q_fake"}}], "id": "page1"}], "title": {"fr": "Ma grande forme", "en": "Not an Original Title"}}'

    >>> df.configuration = None
    >>> df.configuration is None
    True
    >>> df.configuration_json is None
    True


DraftForms can be checked for equality. Note that equality is only defined as
being the same class with the same UID::

    >>> form1 = DraftForm('foo789', channel, div, FORM)
    >>> form2 = DraftForm('foo999', channel, div, FORM)
    >>> form3 = DraftForm('foo789', channel, div, FORM_NOTITLE)
    >>> form1 == form2
    False
    >>> form1 == form3
    True
    >>> form1 != form2
    True
    >>> form1 != form3
    False
    >>> mylist = [form1]
    >>> form1 in mylist
    True
    >>> form2 in mylist
    False
    >>> form3 in mylist
    True
    >>> myset = set(mylist)
    >>> form1 in myset
    True
    >>> form2 in myset
    False
    >>> form3 in myset
    True

    >>> form1 < form2
    True
    >>> form1 <= form3
    True
    >>> form2 > form1
    True
    >>> form3 >= form1
    True
