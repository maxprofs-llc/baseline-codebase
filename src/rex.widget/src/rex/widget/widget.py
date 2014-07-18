#
# Copyright (c) 2014, Prometheus Research, LLC
#


import re
import json
import yaml
from collections import namedtuple
from webob import Response
from webob.exc import HTTPBadRequest, HTTPMethodNotAllowed
from rex.core import (
        Error, Extension, RecordField,
        ProxyVal, StrVal, cached
        )
from .state import (
        ApplicationState, fetch_state, fetch_state_update,
        DataReference, State)


# FIXME: XSS! via script_name
TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta http-equiv="X-UA-Compatible" content="IE=edge">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <link rel="stylesheet" href="%(script_name)s/bundle/bundle.css">
</head>
<body>
  <div id="__main__"></div>
  <script>
    var __MOUNT_PREFIX__ = "%(script_name)s";
  </script>
  <script src="%(script_name)s/bundle/bundle.js"></script>
  <script>
    var __REX_WIDGET__ = %(spec)s;
    if (window.Rex === undefined || window.Rex.Widget === undefined) {
      throw new Error('include rex-widget bower package in your application');
    }
    Rex.Widget.renderSpec(
      __REX_WIDGET__,
      document.getElementById('__main__')
    );
  </script>
</body>
</html>
"""

WidgetDescriptor = namedtuple(
        'WidgetDescriptor',
        ['widget', 'state'])


class Widget(Extension):

    name = None
    fields = []

    validate = ProxyVal()

    class __metaclass__(Extension.__metaclass__):

        def __new__(mcls, name, bases, members):
            cls = Extension.__metaclass__.__new__(mcls, name, bases, members)
            if 'fields' in members:
                cls.fields = [
                        RecordField(*field)
                            if isinstance(field, tuple) else field
                        for field in cls.fields]
            return cls

    @classmethod
    def enabled(cls):
        return (cls.name is not None)

    @classmethod
    @cached
    def map_all(cls):
        mapping = {}
        for extension in cls.all():
            # FIXME: include full module path to already registered and to-be
            # registered module classes
            assert extension.name not in mapping, \
                "duplicate widget %r defined by '%r' and '%r'" % (
                    extension.name, mapping[extension.name], extension)
            mapping[extension.name] = extension
        return mapping

    @classmethod
    def parse(cls, stream):
        if isinstance(stream, (str, unicode)) or hasattr(stream, 'read'):
            return cls.validate.parse(stream)
        else:
            return cls.validate(stream)

    def __init__(self, *args, **kwds):
        # Convert any keywords to positional arguments.
        args_tail = []
        for field in self.fields[len(args):]:
            attribute = field.attribute
            if attribute in kwds:
                args_tail.append(kwds.pop(attribute))
            elif field.has_default:
                args_tail.append(field.default)
            else:
                raise TypeError("missing field %r" % attribute)
        args = args + tuple(args_tail)
        # Complain if there are any keywords left.
        if kwds:
            attr = sorted(kwds)[0]
            if any(field.attribute == attr for field in self.fields):
                raise TypeError("duplicate field %r" % attr)
            else:
                raise TypeError("unknown field %r" % attr)
        # Assign field values.
        if len(args) != len(self.fields):
            raise TypeError("expected %d arguments, got %d"
                            % (len(self.fields), len(args)))
        self.values = {}
        for arg, field in zip(args, self.fields):
            setattr(self, field.attribute, arg)
            self.values[field.attribute] = arg

    def descriptor(self, req):
        props = {}
        state = ApplicationState()

        for name, value in self.values.items():

            name = to_camelcase(name)

            if isinstance(value, Widget):
                descriptor = value.descriptor(req)
                state.update(descriptor.state)
                props[name] = descriptor.widget
            elif isinstance(value, DataReference):
                state_id = "%s.%s" % (self.id, name)
                props[name] = {"__state_read__": state_id}
                state.add(state_id, value, dependencies=value.dependencies, remote=True)
            elif isinstance(value, State):
                state_id = "%s.%s" % (self.id, name)
                props[name] = {"__state_read_write__": state_id}
                state.add(state_id, value.initial)
            else:
                props[name] = value

        return WidgetDescriptor(
                {"__type__": self.js_type, "props": props},
                state)

    def __call__(self, req):
        accept = req.accept.best_match(['text/html', 'application/json'])
        if accept == 'application/json':
            return Response(
                json.dumps(self.as_json(req), cls=WidgetJSONEncoder),
                content_type='application/json')
        else:
            return Response(self.as_html(req))

    def as_html(self, req):
        # XXX: The indent=2 is useful for debug/introspection but hurts bytesize,
        # can we turn it on only in dev mode?
        spec = self.as_json(req)
        spec = WidgetJSONEncoder(indent=2).encode(spec)
        return TEMPLATE % {"spec": spec, "script_name": req.script_name}

    def as_json(self, req):
        widget, state = self.descriptor(req)

        if req.method == 'GET':
            state = fetch_state(state)
            return {"widget": widget, "state": state}

        elif req.method == 'POST':

            origin = None

            for id, value in req.POST.items():
                if id.startswith('update:'):
                    if origin is not None:
                        raise HTTPBadRequest("only single update:* parameter is supported")
                    id = id[7:]
                    origin = id

                if not id in state:
                    raise HTTPBadRequest("invalid state id: %s" % id)

                state[id] = state[id]._replace(value=value)

            if origin is None:
                state = fetch_state(state)
            else:
                state = fetch_state_update(state, origin)

            return {"state": state}

        else:
            raise HTTPMethodNotAllowed()

    def __str__(self):
        text = yaml.dump(self, Dumper=WidgetYAMLDumper)
        return text.rstrip()

    def __repr__(self):
        args = []
        for field in self.fields:
            value = getattr(self, field.attribute)
            if field.has_default and field.default == value:
                continue
            args.append("%s=%r" % (field.attribute, value))
        return "%s(%s)" % (self.__class__.__name__, ", ".join(args))


class GroupWidget(Widget):

    fields = [
            ('children', Widget.validate),
    ]

    def descriptor(self, req):
        state = ApplicationState()
        children = []

        for child in self.children:
            descriptor = child.descriptor(req)
            state.update(descriptor.state)
            children.append(descriptor.widget)

        return WidgetDescriptor({"__children__": children}, state)


class NullWidget(Widget):

    singleton = None

    def __new__(cls):
        if cls.singleton is None:
            cls.singleton = Widget.__new__(cls)
        return cls.singleton

    def descriptor(self, req):
        return WidgetDescriptor(None, ApplicationState())


class WidgetJSONEncoder(json.JSONEncoder):

    def default(self, obj):
        if isinstance(obj, ApplicationState):
            return {k: v._asdict() for k, v in obj.items()}
        return super(WidgetJSONEncoder, self).default(obj)

    def encode(self, obj):
        # XXX: Check if we need more aggresive escape here!
        return super(WidgetJSONEncoder, self).encode(obj).replace('</', '<\\/')


class WidgetYAMLDumper(yaml.Dumper):

    def represent_unicode(self, data):
        return self.represent_scalar(u'tag:yaml.org,2002:str', data)

    def represent_widget(self, data):
        if isinstance(data, GroupWidget):
            return self.represent_sequence(u'tag:yaml.org,2002:seq',
                                           data.children)
        if isinstance(data, NullWidget):
            return self.represent_scalar(u'tag:yaml.org,2002:null', u'')
        tag = unicode(data.name)
        mapping = []
        for field in data.fields:
            value = getattr(data, field.attribute)
            if field.has_default and field.default == value:
                continue
            mapping.append((field.name, value))
        if mapping:
            return self.represent_mapping(tag, mapping, flow_style=False)
        else:
            return self.represent_scalar(tag, u"")


WidgetYAMLDumper.add_representer(
        unicode, WidgetYAMLDumper.represent_unicode)
WidgetYAMLDumper.add_multi_representer(
        Widget, WidgetYAMLDumper.represent_widget)


to_camelcase_re = re.compile(r'_([a-zA-Z])')

def to_camelcase(s):
    return to_camelcase_re.sub(lambda m: m.group(1).upper(), s)


def capitalize(s):
    return s[:1].upper() + s[1:]
