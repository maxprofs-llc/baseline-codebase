#
# Copyright (c) 2006-2013, Prometheus Research, LLC
#


from . import classify, introspect, pattern
from ...core.addon import Addon, Parameter
from ...core.validator import SeqVal, MapVal
from .pattern import (TablePatternVal, ColumnPatternVal, UniqueKeyPatternVal,
        ForeignKeyPatternVal, ClassPatternVal, FieldPatternVal,
        GlobalPatternVal, CommandPatternVal, LabelVal, QLabelVal, CommandVal)
from .introspect import UnusedPatternCache
from .classify import validate


class TweakOverrideAddon(Addon):

    name = 'tweak.override'
    hint = """adjust database metadata"""
    help = """
    This addon provides several ways to adjust database metadata.
    It allows you to restrict access to specific tables and columns,
    specify additional database constraints, change the names of
    tables, columns and links, and define calculated attributes.

    Parameter `included-tables` is a list of tables allowed to be used
    by HTSQL.  Any table not in this list is completely hidden from
    the HTSQL processor.  Each table in the list must have the form
    `<table>` or `<schema>.<table>` and may include `*` symbol to
    indicate any number of characters.

    Parameter `excluded-tables` is a list of tables which are not
    allowed to be used by HTSQL.  When both `included-tables` and
    `excluded-tables` are specified, the only tables available
    are those which are in the `included-tables` list, but not in
    the `excluded-tables` list.

    Parameter `included-columns` is a list of columns allowed to be
    used by HTSQL.  Any column not in this list is completely hidden
    from the HTSQL processor.  The column must have the form
    `<column>`, `<table>.<column>` or `<schema>.<table>.<column>`
    and may include `*` symbol to indicate any number of characters.

    Parameter `excluded-columns` is a list of columns not allowed to
    be used by HTSQL.

    Parameter `not-nulls` is a list of columns with a `NOT NULL`
    constraint.

    Parameter `unique-keys` is a list of `UNIQUE` and `PRIMARY KEY`
    constraints.  Each constraint definition must have a form:
    `<table>(<column>, ...)`, optionally followed by `!` symbol.
    The `!` symbol indicates a `PRIMARY KEY` constraint.

    Parameter `foreign-keys` is a list of `FOREIGN KEY` constraints.
    Each constraint definition must have the form:
    `<table>(<column>,...) -> <table>(<column>,...)`,

    Parameter `class-labels` is a mapping of labels to class
    definitions.  Each class definition is either a table name
    or an HTSQL expression wrapped in parentheses.

    Parameter `field-labels` is a mapping of qualified labels to
    field definitions.  Each field definition is either a column name,
    a comma-separated list of `FOREIGN KEY` and reverse `FOREIGN KEY`
    constraints, or an HTSQL expression.

    Parameter `field-orders` is a mapping of table labels to lists
    of fields to be displayed when an explicit selector is not
    provided.

    Parameter `unlabeled-tables` is a list of tables hidden from
    the user.  The tables could still be used in SQL generated by
    the HTSQL translator.

    Parameter `unlabeled-columns` is a list of columns hidden from
    the user.  The columns could still be used in SQL generated by
    the HTSQL translator.

    Parameter `globals` is a mapping of global definitions to
    an HTSQL expression.

    Parameter `commands` maps command name with parameters to command
    body.
    """

    parameters = [
            Parameter('included_tables', SeqVal(TablePatternVal()),
                      default=[],
                      value_name="TABLES",
                      hint="""permitted tables"""),
            Parameter('excluded_tables', SeqVal(TablePatternVal()),
                      default=[],
                      value_name="TABLES",
                      hint="""forbidden tables"""),
            Parameter('included_columns', SeqVal(ColumnPatternVal()),
                      default=[],
                      value_name="COLUMNS",
                      hint="""permitted columns"""),
            Parameter('excluded_columns', SeqVal(ColumnPatternVal()),
                      default=[],
                      value_name="COLUMNS",
                      hint="""forbidden columns"""),
            Parameter('not_nulls', SeqVal(ColumnPatternVal()),
                      default=[],
                      value_name="COLUMNS",
                      hint="""`NOT NULL` constraints"""),
            Parameter('unique_keys', SeqVal(UniqueKeyPatternVal()),
                      default=[],
                      value_name="KEYS",
                      hint="""`UNIQUE` and `PRIMARY KEY` constraints"""),
            Parameter('foreign_keys', SeqVal(ForeignKeyPatternVal()),
                      default=[],
                      value_name="KEYS",
                      hint="""`FOREIGN KEY` constraints`"""),
            Parameter('class_labels', MapVal(LabelVal(), ClassPatternVal()),
                      default={},
                      value_name="LABELS",
                      hint="""labels for tables and calculations"""),
            Parameter('field_labels', MapVal(QLabelVal(), FieldPatternVal()),
                      default={},
                      value_name="LABELS",
                      hint="""labels for table fields"""),
            Parameter('field_orders', MapVal(LabelVal(), SeqVal(LabelVal())),
                      default={},
                      value_name="LABELS",
                      hint="""default table fields"""),
            Parameter('unlabeled_tables', SeqVal(TablePatternVal()),
                      default=[],
                      value_name="TABLES",
                      hint="""ignored tables"""),
            Parameter('unlabeled_columns', SeqVal(ColumnPatternVal()),
                      default=[],
                      value_name="COLUMNS",
                      hint="""ignored columns"""),
            Parameter('globals', MapVal(LabelVal(), GlobalPatternVal()),
                      default={},
                      value_name="LABELS",
                      hint="""global definitions"""),
            Parameter('commands', MapVal(CommandVal(), CommandPatternVal()),
                      default={},
                      value_name="COMMANDS",
                      hint="""command definitions"""),
    ]

    def __init__(self, app, attributes):
        super(TweakOverrideAddon, self).__init__(app, attributes)
        self.unused_pattern_cache = UnusedPatternCache()
        self.globals_cache = []
        self.commands_cache = []
        for name, parameters in sorted(self.globals):
            adapter = self.globals[name, parameters].register(app, name,
                                                              parameters)
            self.globals_cache.append(adapter)
        for name, parameters in sorted(self.commands):
            adapter = self.commands[name, parameters].register(
                    app, name, parameters)
            self.commands_cache.append(adapter)

    def validate(self):
        validate()
        unused_patterns = self.unused_pattern_cache.patterns
        if unused_patterns:
            raise ValueError("unused override patterns: %s"
                             % ", ".join(unused_patterns))


