#
# Copyright (c) 2006-2012, Prometheus Research, LLC
#


from ... import __version__, __legal__
from ...core.util import maybe, listof
from ...core.context import context
from ...core.adapter import Adapter, adapt, adapt_many, call
from ...core.error import HTTPError, PermissionError, MarkedError
from ...core.domain import (Domain, BooleanDomain, NumberDomain, DateTimeDomain,
                            ListDomain, RecordDomain)
from ...core.syn.syntax import StringSyntax, IntegerSyntax, IdentifierSyntax
from ...core.cmd.command import UniversalCmd, Command, DefaultCmd
from ...core.cmd.summon import Summon, RecognizeError
from ...core.cmd.act import (Act, Action, RenderAction, UnsupportedActionError,
                             act, produce, safe_produce, analyze)
from ...core.model import HomeNode, InvalidNode, InvalidArc
from ...core.classify import classify, normalize
from ...core.tr.bind import bind
from ...core.tr.signature import Signature, Slot
from ...core.fmt.json import (escape_json, dump_json, JS_SEQ, JS_MAP, JS_END,
                              to_raw, profile_to_raw)
from ...core.fmt.html import Template
from ..resource.locate import locate
import re
import cgi
import wsgiref.util


class ShellCmd(Command):

    def __init__(self, query=None, is_implicit=False, mark=None):
        super(ShellCmd, self).__init__(mark)
        assert isinstance(query, maybe(unicode))
        assert isinstance(is_implicit, bool)
        self.query = query
        self.is_implicit = is_implicit


class CompleteCmd(Command):

    def __init__(self, names, mark):
        super(CompleteCmd, self).__init__(mark)
        assert isinstance(names, listof(unicode))
        self.names = names


class ProduceCmd(Command):

    def __init__(self, query, page=None, mark=None):
        super(ProduceCmd, self).__init__(mark)
        assert isinstance(query, unicode)
        assert isinstance(page, maybe(int))
        if page is None:
            page = 1
        self.query = query
        self.page = page


class AnalyzeCmd(Command):

    def __init__(self, query, mark):
        super(AnalyzeCmd, self).__init__(mark)
        assert isinstance(query, unicode)
        self.query = query


class WithPermissionsCmd(Command):

    def __init__(self, command, can_read, can_write, mark):
        super(WithPermissionsCmd, self).__init__(mark)
        assert isinstance(command, Command)
        assert isinstance(can_read, bool)
        assert isinstance(can_write, bool)
        self.command = command
        self.can_read = can_read
        self.can_write = can_write


class ShellSig(Signature):

    slots = [
            Slot('query', is_mandatory=False),
    ]


class CompleteSig(Signature):

    slots = [
            Slot('names', is_mandatory=False, is_singular=False),
    ]


class ProduceSig(Signature):

    slots = [
            Slot('query'),
            Slot('page', is_mandatory=False),
    ]


class AnalyzeSig(Signature):

    slots = [
            Slot('query'),
    ]


class WithPermissionsSig(Signature):

    slots = [
            Slot('query'),
            Slot('can_read'),
            Slot('can_write'),
    ]


class SummonShell(Summon):

    call('shell')

    def __call__(self):
        query = None
        if self.arguments:
            if len(self.arguments) != 1:
                raise RecognizeError("expected no or 1 argument",
                                     self.syntax.mark)
            [syntax] = self.arguments
            if isinstance(syntax, StringSyntax):
                query = syntax.text
            else:
                query = unicode(syntax)
        command = ShellCmd(query, False, self.syntax.mark)
        return command


class SummonComplete(Summon):

    call('complete')

    def __call__(self):
        names = []
        for syntax in self.arguments:
            if not isinstance(syntax, (IdentifierSyntax, StringSyntax)):
                raise RecognizeError("an identifier is required", syntax.mark)
            if isinstance(syntax, IdentifierSyntax):
                name = syntax.name
            else:
                name = syntax.text
            names.append(name)
        command = CompleteCmd(names, self.syntax.mark)
        return command


class SummonProduce(Summon):

    call('produce')

    def __call__(self):
        if not (1 <= len(self.arguments) <= 2):
            raise RecognizeError("expected 1 or 2 arguments",
                                 self.syntax.mark)
        query = self.arguments[0]
        if not isinstance(query, StringSyntax):
            raise RecognizeError("a string literal is required", query.mark)
        query = query.text
        page = None
        if len(self.arguments) == 2:
            page = self.arguments[1]
            if not isinstance(page, IntegerSyntax):
                raise RecognizeError("an integer literal is required", page.mark)
            page = page.value
        command = ProduceCmd(query, page, self.syntax.mark)
        return command


class SummonAnalyze(Summon):

    call('analyze')

    def __call__(self):
        if len(self.arguments) != 1:
            raise RecognizeError("expected 1 argument",
                                 self.syntax.mark)
        query = self.arguments[0]
        if not isinstance(query, StringSyntax):
            raise RecognizeError("a string literal is required", query.mark)
        query = query.text
        command = AnalyzeCmd(query, self.syntax.mark)
        return command


class SummonWithPermissions(Summon):

    call('with_permissions')

    def __call__(self):
        if len(self.arguments) != 3:
            raise RecognizeError("expected 3 arguments", self.syntax.mark)
        query, can_read, can_write = self.arguments
        literals = [can_read, can_write]
        values = []
        domain = BooleanDomain()
        for literal in literals:
            if not isinstance(literal, StringSyntax):
                raise RecognizeError("a string literal is required",
                                     literal.mark)
            try:
                value = domain.parse(literal.text)
            except ValueError, exc:
                raise RecognizeError(str(exc), literal.mark)
            values.append(value)
        can_read, can_write = values
        with context.env(can_read=context.env.can_read and can_read,
                         can_write=context.env.can_write and can_write):
            query = recognize(query)
        command = WithPermissionsCmd(query, can_read, can_write,
                                     self.syntax.mark)
        return command


class RenderShell(Act):

    adapt(ShellCmd, RenderAction)

    def __call__(self):
        query = self.command.query
        resource = locate('/shell/index.html')
        assert resource is not None
        database_name = context.app.htsql.db.database.decode('utf-8', 'replace')
        htsql_version = __version__.decode('ascii')
        htsql_legal = __legal__.decode('ascii')
        server_root = context.app.tweak.shell.server_root
        if server_root is None:
            server_root = wsgiref.util.application_uri(self.action.environ)
        if server_root.endswith('/'):
            server_root = server_root[:-1]
        server_root = server_root.decode('utf-8')
        resource_root = (server_root + '/%s/shell/'
                         % context.app.tweak.resource.indicator)
        resource_root = resource_root.decode('utf-8')
        if query is not None and query not in [u'', u'/']:
            query_on_start = query
            evaluate_on_start = u'true'
        else:
            query_on_start = u'/'
            evaluate_on_start = u'false'
        can_read_on_start = unicode(context.env.can_read).lower()
        can_write_on_start = unicode(context.env.can_write).lower()
        implicit_shell = unicode(self.command.is_implicit).lower()
        status = '200 OK'
        headers = [('Content-Type', 'text/html; charset=UTF-8')]
        template = Template(resource.data)
        body = template(resource_root=cgi.escape(resource_root, True),
                        database_name=cgi.escape(database_name, True),
                        htsql_version=cgi.escape(htsql_version, True),
                        htsql_legal=cgi.escape(htsql_legal, True),
                        server_root=cgi.escape(server_root, True),
                        query_on_start=cgi.escape(query_on_start, True),
                        evaluate_on_start=cgi.escape(evaluate_on_start, True),
                        can_read_on_start=cgi.escape(can_read_on_start, True),
                        can_write_on_start=cgi.escape(can_write_on_start, True),
                        implicit_shell=cgi.escape(implicit_shell, True))
        body = (chunk.encode('utf-8') for chunk in body)
        return (status, headers, body)

    def patch(self, data, prefix, value):
        pattern = prefix + r'="[^"]*"'
        replacement = prefix + '="%s"' % cgi.escape(value, True)
        data, count = re.subn(pattern, replacement, data, 1)
        assert count == 1
        return data


class RenderComplete(Act):

    adapt(CompleteCmd, RenderAction)

    def __call__(self):
        identifiers = self.command.names
        nodes = []
        labels_by_node = {}
        names_by_node = {}
        node = HomeNode()
        labels = classify(node)
        labels = [label for label in labels
                        if not isinstance(label.arc, InvalidArc)]
        nodes.append(node)
        labels_by_node[node] = labels
        names_by_node[node] = dict((label.name, label) for label in labels)
        for identifier in identifiers:
            identifier = normalize(identifier)
            nodes_copy = nodes[:]
            while nodes:
                node = nodes[-1]
                label = names_by_node[node].get(identifier)
                if label is not None:
                    break
                nodes.pop()
            node = label.target if label is not None else InvalidNode()
            nodes = nodes_copy
            nodes.append(node)
            if node not in labels_by_node:
                labels = classify(node)
                labels = [label
                          for label in labels
                          if not isinstance(label.arc, InvalidArc)]
                labels_by_node[node] = labels
                names_by_node[node] = dict((label.name, label)
                                           for label in labels)
        node = nodes[-1]
        labels = labels_by_node[node]
        names = [label.name for label in labels]
        status = '200 OK'
        headers = [('Content-Type', 'application/javascript')]
        body = (line.encode('utf-8')
                for line in dump_json(self.render_names(names)))
        return (status, headers, body)

    def render_names(self, names):
        yield JS_MAP
        yield u"type"
        yield u"complete"
        yield u"names"
        yield JS_SEQ
        for name in names:
            yield name
        yield JS_END
        yield JS_END


class RenderProduceAnalyze(Act):

    adapt_many((ProduceCmd, RenderAction),
               (AnalyzeCmd, RenderAction))

    def __call__(self):
        addon = context.app.tweak.shell
        status = "200 OK"
        headers = [('Content-Type', 'application/javascript')]
        command = UniversalCmd(self.command.query.encode('utf-8'))
        limit = None
        try:
            if isinstance(self.command, AnalyzeCmd):
                plan = analyze(command)
            else:
                page = self.command.page
                if page is not None and page > 0 and addon.limit is not None:
                    limit = page*addon.limit
                if limit is not None:
                    product = safe_produce(command, limit+1)
                else:
                    product = produce(command)
        except UnsupportedActionError, exc:
            body = self.render_unsupported(exc)
        except PermissionError, exc:
            body = self.render_permissions(exc)
        except HTTPError, exc:
            body = self.render_error(exc)
        else:
            if isinstance(self.command, AnalyzeCmd):
                body = self.render_sql(plan)
            else:
                if product:
                    body = self.render_product(product, limit)
                else:
                    body = self.render_empty()
        body = (line.encode('utf-8') for line in dump_json(body))
        return (status, headers, body)

    def render_unsupported(self, exc):
        yield JS_MAP
        yield u"type"
        yield u"unsupported"
        yield JS_END

    def render_permissions(self, exc):
        detail = exc.detail.decode('utf-8')
        yield JS_MAP
        yield u"type"
        yield u"permissions"
        yield u"detail"
        yield detail
        yield JS_END

    def render_error(self, exc):
        detail = exc.detail.decode('utf-8')
        hint = None
        first_line = None
        first_column = None
        last_line = None
        last_column = None
        if isinstance(exc, MarkedError) and exc.mark.text:
            mark = exc.mark
            first_break = mark.text.rfind(u'\n', 0, mark.start)+1
            last_break = mark.text.rfind(u'\n', 0, mark.end)+1
            first_line = mark.text.count(u'\n', 0, first_break)
            last_line = mark.text.count(u'\n', 0, last_break)
            first_column = mark.start-first_break
            last_column = mark.end-last_break
            hint = exc.hint
        if hint is not None:
            hint = hint.decode('utf-8')
        yield JS_MAP
        yield u"type"
        yield u"error"
        yield u"detail"
        yield detail
        yield u"hint"
        yield hint
        yield u"first_line"
        yield first_line
        yield u"first_column"
        yield first_column
        yield u"last_line"
        yield last_line
        yield u"last_column"
        yield last_column
        yield JS_END

    def render_product(self, product, limit):
        yield JS_MAP
        yield u"type"
        yield u"product"
        yield u"meta"
        for token in profile_to_raw(product.meta):
            yield token
        yield u"data"
        product_to_raw = to_raw(product.meta.domain)
        data = product.data
        if limit is not None and isinstance(data, list) and len(data) > limit:
            data = data[:limit]
        for token in product_to_raw(data):
            yield token
        yield u"more"
        yield (limit is not None and
               isinstance(product.data, list) and
               len(product.data) > limit)
        yield JS_END

    def render_empty(self):
        yield JS_MAP
        yield u"type"
        yield u"empty"
        yield JS_END

    def render_sql(self, plan):
        if plan.statement is not None:
            sql = []
            queue = [plan.statement]
            while queue:
                statement = queue.pop(0)
                sql.append(statement.sql)
                queue.extend(statement.substatements)
            sql = u"\n".join(sql)
        else:
            sql = u""
        yield JS_MAP
        yield u"type"
        yield u"sql"
        yield u"sql"
        yield sql
        yield JS_END


class ActWithPermissions(Act):

    adapt(WithPermissionsCmd, Action)

    def __call__(self):
        can_read = context.env.can_read and self.command.can_read
        can_write = context.env.can_write and self.command.can_write
        with context.env(can_read=can_read, can_write=can_write):
            return act(self.command.command, self.action)


