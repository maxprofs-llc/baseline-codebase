#
# Copyright (c) 2006-2012, Prometheus Research, LLC
# See `LICENSE` for license information, `AUTHORS` for the list of authors.
#


"""
:mod:`htsql.core.fmt.html`
==========================

This module implements the HTML renderer.
"""


from ..util import listof, tupleof, maybe, Printable
from ..adapter import Adapter, adapts, adapts_many
from .format import HTMLFormat, EmitHeaders, Emit
from .format import Renderer
from ..mark import Mark
from ..error import InternalServerError
from ..domain import (Domain, BooleanDomain, NumberDomain, DecimalDomain,
                      StringDomain, EnumDomain, DateDomain,
                      TimeDomain, DateTimeDomain, ListDomain, RecordDomain,
                      VoidDomain, OpaqueDomain, Profile)
import pkg_resources
import cgi
import re


class Block(Printable):

    def __init__(self, mark):
        assert isinstance(mark, Mark)
        self.mark = mark


class TextBlock(Block):

    def __init__(self, text, mark):
        assert isinstance(text, unicode)
        super(TextBlock, self).__init__(mark)
        self.text = text

    def __str__(self):
        lines = self.text.splitlines()
        if len(lines) == 0:
            line = ""
        elif len(lines) == 1:
            line = lines[0].rstrip().encode('utf-8')
        else:
            line = lines[0].rstrip().encode('utf-8')+'...'
        return line


class EchoBlock(Block):

    def __init__(self, name, mark):
        assert isinstance(name, str)
        super(EchoBlock, self).__init__(mark)
        self.name = name

    def __str__(self):
        return "{{ %s }}" % self.name


class ClauseBlock(Block):

    def __init__(self, action, names, mark):
        assert isinstance(action, str)
        assert isinstance(names, listof(str))
        super(ClauseBlock, self).__init__(mark)
        self.action = action
        self.names = names

    def __str__(self):
        if self.names:
            return "{%% %s %s %%}" % (self.action, " ".join(self.names))
        else:
            return "{%% %s %%}" % self.action


class Case(Printable):
    pass


class TextCase(Case):

    def __init__(self, text):
        assert isinstance(text, unicode)
        self.text = text

    def __str__(self):
        lines = self.text.splitlines()
        if len(lines) == 0:
            line = ""
        elif len(lines) == 1:
            line = lines[0].rstrip().encode('utf-8')
        else:
            line = lines[0].rstrip().encode('utf-8')+'...'
        return line


class EchoCase(Case):

    def __init__(self, name, mark):
        assert isinstance(name, str)
        assert isinstance(mark, Mark)
        self.name = name
        self.mark = mark

    def __str__(self):
        return "{{ %s }}" % self.name


class BranchCase(Case):

    def __init__(self, choices):
        assert isinstance(choices, listof(tupleof(maybe(str), Case, Mark)))
        self.choices = choices

    def __str__(self):
        chunks = []
        is_first = True
        for name, case, mark in self.choices:
            if name is not None:
                if is_first:
                    chunks.append("{%% if %s %%}" % name)
                    is_first = False
                else:
                    chunks.append("{%% elif %s %%}" % name)
            else:
                chunks.append("{% else %}")
            chunks.append(str(case))
        chunks.append("{% endif %}")
        return "".join(chunks)


class SequenceCase(Case):

    def __init__(self, cases):
        assert isinstance(cases, listof(Case))
        self.cases = cases

    def __str__(self):
        return "".join(str(case) for case in self.cases)


class TemplateError(InternalServerError):

    def __init__(self, detail, mark):
        self.detail = detail
        self.mark = mark

    def __str__(self):
        excerpt = "\n".join("    "+line.encode('utf-8')
                            for line in self.mark.excerpt())
        return "%s: %s:\n%s" % (self.kind, self.detail, excerpt)


class Template(object):

    text_pattern = r"""
        (?: [^{] | [{] [^{%#] )+
    """
    expr_pattern = r"""
        (?:
            (?P<echo>
                [{][{] \s*
                (?P<name> [A-Za-z_][0-9A-Za-z_]* )
                \s* [}][}]
            ) |
            (?P<clause>
                [{][%] \s*
                (?P<action> [A-Za-z_][0-9A-Za-z_]* )
                (?P<names> (?: \s+ [A-Za-z_][0-9A-Za-z_]* )* )
                \s* [%][}]
            ) |
            (?P<comment>
                [{][#] (?: [^#] | [#][^}] )* [#][}]
            )
        ) (?: [ \t]* \r?\n )?
    """
    text_regexp = re.compile(text_pattern, re.X)
    expr_regexp = re.compile(expr_pattern, re.X)

    def __init__(self, stream):
        blocks = self.scan(stream)
        case = self.parse(blocks)
        self.case = case

    def scan(self, stream):
        input = stream.read()
        if isinstance(input, str):
            try:
                input = input.decode('utf-8')
            except UnicodeDecodeError, exc:
                mark = Mark(input.decode('utf-8', 'replace'),
                            exc.start, exc.end)
                raise TemplateError("invalid UTF-8 character (%s)"
                                    % exc.reason, mark)
        pos = 0
        while pos < len(input):
            match = self.text_regexp.match(input, pos)
            if match is not None:
                text = match.group()
                mark = Mark(input, match.start(), match.end())
                yield TextBlock(text, mark)
                pos = match.end()
                if pos == len(input):
                    break
            match = self.expr_regexp.match(input, pos)
            if match is None:
                mark = Mark(input, pos, pos)
                raise TemplateError("invalid template expression", mark)
            if match.group('echo') is not None:
                name = match.group('name').encode('utf-8')
                mark = Mark(input, match.start('echo'), match.end('echo'))
                yield EchoBlock(name, mark)
            elif match.group('clause') is not None:
                action = match.group('action').encode('utf-8')
                names = match.group('names').encode('utf-8').split()
                mark = Mark(input, match.start('clause'), match.end('clause'))
                yield ClauseBlock(action, names, mark)
            pos = match.end()

    def parse(self, blocks):
        blocks = list(blocks)
        case = self.parse_sequence(blocks)
        if blocks:
            raise TemplateError("unexpected clause", blocks[0].mark)
        return case

    def parse_sequence(self, blocks):
        cases = []
        while blocks:
            if isinstance(blocks[0], TextBlock):
                block = blocks.pop(0)
                case = TextCase(block.text)
            elif isinstance(blocks[0], EchoBlock):
                block = blocks.pop(0)
                case = EchoCase(block.name, block.mark)
            elif (isinstance(blocks[0], ClauseBlock) and
                    blocks[0].action == "if"):
                case = self.parse_branch(blocks)
            else:
                break
            cases.append(case)
        if len(cases) == 1:
            return cases[0]
        return SequenceCase(cases)

    def parse_branch(self, blocks):
        choices = []
        assert blocks
        block = blocks.pop(0)
        assert isinstance(block, ClauseBlock) and block.action == "if"
        if len(block.names) != 1:
            raise TemplateError("expected one parameter", block.mark)
        name = block.names[0]
        case = self.parse_sequence(blocks)
        mark = block.mark
        choices.append((name, case, mark))
        has_else = False
        while True:
            if not blocks:
                raise TemplateError("missing `endif` clause", mark)
            block = blocks.pop(0)
            assert isinstance(block, ClauseBlock)
            if block.action == 'elif' and not has_else:
                if len(block.names) != 1:
                    raise TemplateError("expected one parameter", block.mark)
                name = block.names[0]
                case = self.parse_sequence(blocks)
                choices.append((name, case, block.mark))
            elif block.action == 'else' and not has_else:
                if len(block.names) != 0:
                    raise TemplateError("expected no parameters", block.mark)
                case = self.parse_sequence(blocks)
                choices.append((None, case, block.mark))
                has_else = True
            elif block.action == 'endif':
                if len(block.names) != 0:
                    raise TemplateError("expected no parameters", block.mark)
                break
            else:
                raise TemplateError("unexpected clause", block.mark)
        return BranchCase(choices)

    def __call__(self, **context):
        return self.emit(self.case, context)

    def emit(self, case, context):
        if isinstance(case, TextCase):
            yield case.text
        elif isinstance(case, EchoCase):
            if case.name not in context:
                raise TemplateError("undefined context variable", case.mark)
            value = context[case.name]
            if value is not None:
                assert not isinstance(value, str)
                if isinstance(value, unicode):
                    yield value
                else:
                    for chunk in value:
                        yield chunk
        elif isinstance(case, BranchCase):
            for name, case, mark in case.choices:
                if name is not None:
                    if name not in context:
                        raise TemplateError("undefined context variable", mark)
                    value = context[case.name]
                    if value is None or value == u"":
                        continue
                for chunk in self.emit(case, context):
                    yield chunk
                break
        elif isinstance(case, SequenceCase):
            for case in case.cases:
                for chunk in self.emit(case, context):
                    yield chunk


class EmitHTMLHeaders(EmitHeaders):

    adapts(HTMLFormat)

    def __call__(self):
        yield ('Content-Type', 'text/html; charset=UTF-8')


class EmitHTML(Emit):

    adapts(HTMLFormat)

    def __call__(self):
        product_to_html = profile_to_html(self.meta)
        headers_height = product_to_html.headers_height()
        cells_height = product_to_html.cells_height(self.data)
        if self.meta.header:
            title = cgi.escape(self.meta.header, True)
        else:
            title = u""
        content = None
        if headers_height or cells_height:
            content = self.table(product_to_html,
                                 headers_height, cells_height, title)
        stream = pkg_resources.resource_stream(__name__,
                                               "static/template.html")
        template = Template(stream)
        return template(title=title, content=content)

    def table(self, product_to_html, headers_height, cells_height, title):
        yield u"<table class=\"htsql-output\" summary=\"%s\">\n" % title
        if headers_height > 0:
            yield u"<thead>\n"
            for row in product_to_html.headers(headers_height):
                yield u"<tr>%s</tr>\n" % u"".join(row)
            yield u"</thead>\n"
        if cells_height > 0:
            yield u"<tbody>\n"
            index = 0
            for row in product_to_html.cells(self.data, cells_height):
                index += 1
                attributes = []
                if index % 2:
                    attributes.append(" class=\"htsql-odd-row\"")
                else:
                    attributes.append(" class=\"htsql-even-row\"")
                yield u"<tr%s>%s</tr>\n" % (u"".join(attributes),
                                            u"".join(row))
            yield u"</tbody>\n"
        yield u"</table>\n"


class ToHTML(Adapter):

    adapts(Domain)

    def __init__(self, domain):
        assert isinstance(domain, Domain)
        self.domain = domain
        self.width = 1

    def __call__(self):
        return self

    def headers(self, height):
        if height > 0:
            attributes = []
            if height == 1:
                attributes.append(u" rowspan=\"%s\"" % height)
            attributes.append(u" class=\"htsql-empty-header\"")
            yield [u"<th%s></th>" % "".join(attributes)]

    def headers_height(self):
        return 0

    def cells(self, value, height):
        assert height > 0
        classes = []
        classes.append(u"htsql-%s-type" % self.domain.family)
        content = self.dump(value)
        if content is None:
            content = u""
            classes.append(u"htsql-null-value")
        elif not content:
            classes.append(u"htsql-empty-value")
        else:
            content = cgi.escape(content)
        classes.extend(self.classes(value))
        attributes = []
        if height > 1:
            attributes.append(u" rowspan=\"%s\"" % height)
        attributes.append(u" class=\"%s\"" % u" ".join(classes))
        yield [u"<td%s>%s</td>" % (u"".join(attributes), content)]

    def cells_height(self, value):
        return 1

    def classes(self, value):
        return []

    def dump(self, value):
        return self.domain.dump(value)


class VoidToHTML(ToHTML):

    adapts(VoidDomain)

    def __init__(self, domain):
        super(VoidToHTML, self).__init__(domain)
        self.width = 0

    def cells_height(self, value):
        return 0


class RecordToHTML(ToHTML):

    adapts(RecordDomain)

    def __init__(self, domain):
        super(RecordToHTML, self).__init__(domain)
        self.fields_to_html = [profile_to_html(field)
                               for field in domain.fields]
        self.width = sum(field_to_html.width
                         for field_to_html in self.fields_to_html)

    def headers(self, height):
        if not self.width:
            return
        streams = [field_to_html.headers(height)
                   for field_to_html in self.fields_to_html]
        is_done = False
        while not is_done:
            is_done = True
            row = []
            for stream in streams:
                subrow = next(stream, None)
                if subrow is not None:
                    row.extend(subrow)
                    is_done = False
            if not is_done:
                yield row

    def headers_height(self):
        if not self.width:
            return 0
        return max(field_to_html.headers_height()
                   for field_to_html in self.fields_to_html)

    def cells(self, value, height):
        if not self.width or not height:
            return
        if value is None:
            attributes = []
            if height > 1:
                attributes.append(u" rowspan=\"%s\"" % height)
            attributes.append(u" class=\"htsql-null-record-value\"")
            yield [u"<td%s></td>" % u"".join(attributes)]*self.width
        else:
            streams = [field_to_html.cells(item, height)
                       for item, field_to_html in zip(value,
                                                      self.fields_to_html)]
            is_done = False
            while not is_done:
                is_done = True
                row = []
                for stream in streams:
                    subrow = next(stream, None)
                    if subrow is not None:
                        row.extend(subrow)
                        is_done = False
                if not is_done:
                    yield row

    def cells_height(self, value):
        if not self.width or value is None:
            return 0
        return max(field_to_html.cells_height(item)
                   for field_to_html, item in zip(self.fields_to_html, value))


class ListToHTML(ToHTML):

    adapts(ListDomain)

    def __init__(self, domain):
        super(ListToHTML, self).__init__(domain)
        self.item_to_html = to_html(domain.item_domain)
        self.width = self.item_to_html.width+1

    def headers(self, height):
        if height > 0:
            item_stream = self.item_to_html.headers(height)
            first_row = next(item_stream)
            attributes = []
            if height > 1:
                attributes.append(u" rowspan=\"%s\"" % height)
            attributes.append(" class=\"htsql-empty-header\"")
            first_row.insert(0, u"<th%s></th>" % u"".join(attributes))
            yield first_row
            for row in item_stream:
                yield row

    def headers_height(self):
        return self.item_to_html.headers_height()

    def cells(self, value, height):
        if not height:
            return
        if not value:
            attributes = []
            if self.width > 1:
                attributes.append(u" colspan=\"%s\"" % self.width)
            if height > 1:
                attributes.append(u" rowspan=\"%s\"" % height)
            attributes.append(u" class=\"htsql-null-value\"")
            yield [u"<td%s></td>" % u"".join(attributes)]
        items = iter(value)
        item = next(items)
        is_last = False
        total_height = height
        index = 1
        while not is_last:
            try:
                next_item = next(items)
            except StopIteration:
                next_item = None
                is_last = True
            item_height = max(1, self.item_to_html.cells_height(item))
            if is_last:
                item_height = total_height
            total_height -= item_height
            item_stream = self.item_to_html.cells(item, item_height)
            first_row = next(item_stream, [])
            attributes = []
            if item_height > 1:
                attributes.append(u" rowspan=\"%s\"" % height)
            attributes.append(u" class=\"htsql-index\"")
            first_row.insert(0, u"<td%s>%s</td>"
                                % (u"".join(attributes), index))
            yield first_row
            for row in item_stream:
                yield row
            item = next_item
            index += 1

    def cells_height(self, value):
        if not value:
            return 0
        return sum(max(1, self.item_to_html.cells_height(item))
                   for item in value)


class NativeToHTML(ToHTML):

    adapts_many(StringDomain,
                EnumDomain)

    def dump(self, value):
        return value


class NativeStringToHTML(ToHTML):

    adapts_many(NumberDomain,
                DateDomain,
                TimeDomain)

    def dump(self, value):
        if value is None:
            return None
        return unicode(value)


class DecimalToHTML(ToHTML):

    adapts(DecimalDomain)

    def dump(self, value):
        if value is None:
            return value
        sign, digits, exp = value.as_tuple()
        if not digits:
            return unicode(value)
        if exp < -6 and value == value.normalize():
            value = value.normalize()
            sign, digits, exp = value.as_tuple()
        if exp > 0:
            value = value.quantize(decimal.Decimal(1))
        return unicode(value)


class BooleanToHTML(ToHTML):

    adapts(BooleanDomain)

    def classes(self, value):
        if value is True:
            return [u"htsql-true-value"]
        if value is False:
            return [u"htsql-false-value"]

    def dump(self, value):
        if value is None:
            return None
        elif value is True:
            return u"true"
        elif value is False:
            return u"false"


class DateTimeToHTML(ToHTML):

    adapts(DateTimeDomain)

    def dump(self, value):
        if value is None:
            return None
        elif not value.time():
            return unicode(value.date())
        else:
            return unicode(value)


class OpaqueToHTML(ToHTML):

    adapts(OpaqueDomain)

    def dump(self, value):
        if value is None:
            return None
        if not isinstance(value, unicode):
            try:
                value = str(value).decode('utf-8')
            except UnicodeDecodeError:
                value = unicode(repr(value))
        return value


class MetaToHTML(object):

    def __init__(self, profile):
        assert isinstance(profile, Profile)
        self.profile = profile
        self.domain_to_html = to_html(profile.domain)
        self.width = self.domain_to_html.width
        self.header_level = self.domain_to_html.headers_height()+1

    def headers(self, height):
        if not self.width or not height:
            return
        if not self.profile.header:
            for row in self.domain_to_html.headers(height):
                yield row
            return
        content = cgi.escape(self.profile.header)
        attributes = []
        if self.width > 1:
            attributes.append(u" colspan=\"%s\"" % self.width)
        if height > 1 and self.header_level == 1:
            attributes.append(u" rowspan=\"%s\"" % height)
        if not content:
            attributes.append(u" class=\"htsql-empty-header\"")
        yield [u"<th%s>%s</th>" % (u"".join(attributes), content)]
        if self.header_level > 1:
            for row in self.domain_to_html.headers(height-1):
                yield row

    def headers_height(self):
        height = self.domain_to_html.headers_height()
        if self.profile.header:
            height += 1
        return height

    def cells(self, value, height):
        return self.domain_to_html.cells(value, height)

    def cells_height(self, value):
        return self.domain_to_html.cells_height(value)


def to_html(domain):
    to_html = ToHTML(domain)
    return to_html

def profile_to_html(profile):
    return MetaToHTML(profile)


class HTMLRenderer(Renderer):

    name = 'text/html'
    aliases = ['html']

    def render(self, product):
        status = self.generate_status(product)
        headers = self.generate_headers(product)
        body = list(self.generate_body(product))
        return status, headers, body

    def generate_status(self, product):
        return "200 OK"

    def generate_headers(self, product):
        format = HTMLFormat()
        emit_headers = EmitHeaders(format, product)
        return list(emit_headers())

    def generate_body(self, product):
        format = HTMLFormat()
        emit_body = Emit(format, product)
        for line in emit_body():
            if isinstance(line, unicode):
                line = line.encode('utf-8')
            yield line


