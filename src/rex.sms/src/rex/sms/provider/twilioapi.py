#
# Copyright (c) 2014, Prometheus Research, LLC
#


import time

from rex.core import get_settings, Error, Setting, StrVal, IntVal
from twilio.rest import TwilioRestClient
from twilio.rest.exceptions import TwilioRestException

from ..errors import BlockedSmsError
from .base import SmsProvider


__all__ = (
    'TwilioSmsProvider',
)


def setting_or_die(name):
    setting = getattr(get_settings(), name, None)
    if setting is None:
        raise Error(
            'Setting %s must be specified.' % (
                name,
            )
        )
    return setting


class TwilioSmsProvider(SmsProvider):
    """
    An implementation of SmsProvider that uses the Twilio API to send the SMS
    messages.
    """

    #: The name of this implementation used by the ``sms_provider`` setting.
    name = 'twilio'

    def __init__(self):
        # pylint: disable=super-on-old-class
        super(TwilioSmsProvider, self).__init__()
        self.client = None

    def initialize(self):
        # pylint: disable=super-on-old-class
        super(TwilioSmsProvider, self).__init__()

        account = setting_or_die('sms_twilio_account_sid')
        token = setting_or_die('sms_twilio_token')
        timeout = setting_or_die('sms_twilio_timeout')

        self.client = TwilioRestClient(
            account=account,
            token=token,
            timeout=timeout,
        )

    def __call__(self, recipient, sender, message):
        attempts = 0
        retry_delay = get_settings().sms_twilio_retry_delay / 1000.0

        while True:
            try:
                attempts += 1
                message = self.client.messages.create(
                    to=recipient,
                    from_=sender,
                    body=message,
                )
                return

            except TwilioRestException as exc:
                if exc.status >= 500:
                    if attempts < get_settings().sms_twilio_max_attempts:
                        time.sleep(retry_delay)
                    else:
                        raise
                elif exc.code == 21610:
                    raise BlockedSmsError(recipient)
                else:
                    raise


class SmsTwilioAccountSidSetting(Setting):
    """
    The Account SID to use when connecting to the Twilio API.
    """

    name = 'sms_twilio_account_sid'
    validate = StrVal()
    default = None


class SmsTwilioTokenSetting(Setting):
    """
    The API Token to use when connecting to the Twilio API.
    """

    name = 'sms_twilio_token'
    validate = StrVal()
    default = None


class SmsTwilioTimeoutSetting(Setting):
    """
    The number of seconds to use as a timeout threshold when accessing the
    Twilio API.

    Defaults to: 5
    """

    name = 'sms_twilio_timeout'
    validate = IntVal()
    default = 5


class SmsTwilioMaxAttemptsSetting(Setting):
    """
    The number of times the system should attempt to invoke the Twilio API if
    it encounters errors from the Twilio server.

    Defaults to: 3
    """

    name = 'sms_twilio_max_attempts'
    validate = IntVal()
    default = 3


class SmsTwilioRetryDelaySetting(Setting):
    """
    The number of milliseconds the use as a delay between failed Twilio API
    attempts.

    Defaults to: 1000
    """

    name = 'sms_twilio_retry_delay'
    validate = IntVal()
    default = 1000

