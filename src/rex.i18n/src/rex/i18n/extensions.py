#
# Copyright (c) 2014, Prometheus Research, LLC
#


from babel import Locale, UnknownLocaleError
from pytz import timezone, UnknownTimeZoneError

from rex.core import Extension, get_settings, cached
from rex.web import HandleTemplate

from .core import KEY_LOCALE, KEY_TIMEZONE, DOMAIN_BACKEND, DOMAIN_FRONTEND


__all__ = (
    'BabelMapper',
    'CoreBabelMapper',
    'WebBabelMapper',
    'JavaScriptBabelMapper',

    'LocaleDetector',
    'SessionLocaleDetector',
    'AcceptLanguageLocaleDetector',
    'DefaultLocaleDetector',

    'TimezoneDetector',
    'SessionTimezoneDetector',
    'DefaultTimezoneDetector',
)


class BabelMapper(Extension):
    domain = None

    @classmethod
    def sanitize(cls):
        if cls.__name__ != 'BabelMapper':
            assert cls.mapper_config != BabelMapper.mapper_config, \
                'abstract method %s.mapper_config()' % cls

    @classmethod
    def enabled(cls):
        return cls.domain is not None

    @classmethod
    def mapper_config(cls):
        raise NotImplementedError()

    @classmethod
    def domain_mapper_config(cls, domain):
        parts = []
        for mapper in cls.all():
            if mapper.domain == domain:
                parts.append(mapper.mapper_config())
        return '\n'.join(parts)


class CoreBabelMapper(BabelMapper):
    domain = DOMAIN_BACKEND

    @classmethod
    def mapper_config(cls):
        return '[python: src/**.py]'


class WebBabelMapper(BabelMapper):
    domain = DOMAIN_BACKEND

    @classmethod
    def mapper_config(cls):
        jinja_extensions = 'extensions=jinja2.ext.do,jinja2.ext.loopcontrols'

        lines = [
            '[jinja2: static/template/**.html]',
            jinja_extensions,
        ]

        for handler in HandleTemplate.all():
            lines.append('[jinja2: static/www/**%s]' % handler.ext)
            lines.append(jinja_extensions)

        return '\n'.join(lines)


class JavaScriptBabelMapper(BabelMapper):
    domain = DOMAIN_FRONTEND

    @classmethod
    def mapper_config(cls):
        lines = [
            '[javascript: static/js/lib/**.js]',
            '[javascript: static/js/lib/**.jsx]',
        ]

        return '\n'.join(lines)


class LocaleDetector(Extension):
    priority = None

    @classmethod
    @cached
    def all(cls):
        return sorted(
            super(LocaleDetector, cls).all(),
            key=lambda e: e.priority,
        )

    @classmethod
    def enabled(cls):
        return cls.priority is not None

    @classmethod
    def sanitize(cls):
        if cls.__name__ != 'LocaleDetector':
            assert cls.detect_locale != LocaleDetector.detect_locale, \
                'abstract method %s.detect_locale()' % cls

    @classmethod
    def detect_locale(cls, request):
        for detector in cls.all():
            locale = detector.detect_locale(request)
            if locale:
                return locale
        return None


class SessionLocaleDetector(LocaleDetector):
    priority = 100

    @classmethod
    def detect_locale(cls, request):
        if 'rex.session' in request.environ \
                and KEY_LOCALE in request.environ['rex.session']:
            lid = request.environ['rex.session'][KEY_LOCALE]
            try:
                return Locale.parse(lid)
            except UnknownLocaleError:
                return None
        return None


class AcceptLanguageLocaleDetector(LocaleDetector):
    priority = 500

    @classmethod
    def detect_locale(cls, request):
        lid = request.accept_language.best_match(
            [l.language for l in get_settings().i18n_supported_locales],
        )
        if lid:
            try:
                return Locale.parse(lid)
            except UnknownLocaleError:
                return None
        return None


class DefaultLocaleDetector(LocaleDetector):
    priority = 1000

    @classmethod
    def detect_locale(cls, request):
        return get_settings().i18n_default_locale


class TimezoneDetector(Extension):
    priority = None

    @classmethod
    @cached
    def all(cls):
        return sorted(
            super(TimezoneDetector, cls).all(),
            key=lambda e: e.priority,
        )

    @classmethod
    def enabled(cls):
        return cls.priority is not None

    @classmethod
    def sanitize(cls):
        if cls.__name__ != 'TimezoneDetector':
            assert cls.detect_timezone != TimezoneDetector.detect_timezone, \
                'abstract method %s.detect_timezone()' % cls

    @classmethod
    def detect_timezone(cls, request):
        for detector in cls.all():
            zone = detector.detect_timezone(request)
            if zone:
                return zone
        return None


class SessionTimezoneDetector(TimezoneDetector):
    priority = 100

    @classmethod
    def detect_timezone(cls, request):
        if 'rex.session' in request.environ \
                and KEY_TIMEZONE in request.environ['rex.session']:
            tzid = request.environ['rex.session'][KEY_TIMEZONE]
            try:
                return timezone(tzid)
            except UnknownTimeZoneError:
                return None
        return None


class DefaultTimezoneDetector(TimezoneDetector):
    priority = 1000

    @classmethod
    def detect_timezone(cls, request):
        return get_settings().i18n_default_timezone
