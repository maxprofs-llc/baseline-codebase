#
# Copyright (c) 2013, Prometheus Research, LLC
#


import decimal
import datetime
import hashlib


def mangle(fragments, suffix=None,
           max_length=63,
           forbidden_prefixes=[u"pg"],
           forbidden_suffixes=[u"id", u"pk", u"uk", u"fk", u"chk", u"enum"]):
    """
    Generates a SQL name from fragments and a suffix.

    `fragment`
        A word or a list of words from which the name is generated.
    `suffix`
        Optional ending.

    :func:`mangle` joins the fragments and the suffix with ``_``.  If necessary,
    it mangles the name to fit the limit on number of characters and avoid naming
    collisions.
    """
    # Accept a single word too.
    if not isinstance(fragments, (list, tuple)):
        fragments = [fragments]
    # Make a separator that is not contained in any fragments.
    separator = u"_"
    while any(separator in fragment for fragment in fragments):
        separator += u"_"
    # Generate the name
    stem = separator.join(fragments)
    text = stem
    if suffix is not None:
        text += separator+suffix
    # Find if the name is collision-prone.
    is_forbidden = (any(stem == syllable or stem.startswith(syllable+u"_")
                        for syllable in forbidden_prefixes) or
                    (suffix is None and
                     any(stem == syllable or stem.endswith(u"_"+syllable)
                         for syllable in forbidden_suffixes)))
    # Mangle the name if it's too long or collision-prone.
    if is_forbidden or len(text) > max_length:
        # Add 6 characters from the MD5 hash to prevent collisions.
        digest = separator+unicode(hashlib.md5(stem).hexdigest()[:6])
        # Cut some characters to reduce the name length if necessary.
        if len(text)+len(digest) > max_length:
            cut_start = max_length/4
            cut_end = cut_start+len(digest)+len(separator)+len(text)-max_length
            text = text[:cut_start]+separator+text[cut_end:]
        text += digest
        assert len(text) <= max_length
    return text


def sql_name(names):
    """
    Quotes a SQL name or a list of names.

    `names`
        Identifier or a list of identifiers.

    If given a list of names, returns a comma-separated sequence of quoted
    identifiers.  Otherwise, returns a quoted identifier.
    """
    if not isinstance(names, (list, tuple)):
        names = [names]
    return u", ".join(u"\"%s\"" % name.replace(u"\"", u"\"\"")
                      for name in names)


def sql_value(value):
    """
    Converts a value to a SQL literal.

    `value`
        SQL value.  Accepted types are ``bool``, ``int``, ``long``, ``float``,
        ``decimal.Decimal``, ``str``, ``unicode`` or ``None``.  Also accepted
        are lists or tuples of acceptable values.
    """
    if value is None:
        return u"NULL"
    if isinstance(value, bool):
        if value is True:
            return u"TRUE"
        if value is False:
            return u"FALSE"
    if isinstance(value, (int, long, float, decimal.Decimal)):
        # FIXME: accept finite numbers only.
        return unicode(value)
    if isinstance(value, (datetime.date, datetime.time, datetime.datetime)):
        return u"'%s'" % value
    if isinstance(value, (str, unicode)):
        value = value.replace(u"'", u"''")
        if u"\\" in value:
            value = value.replace(u"\\", u"\\\\")
            return u"E'%s'" % value
        else:
            return u"'%s'" % value
    if isinstance(value, (list, tuple)):
        return u", ".join(sql_value(item) for item in value)
    raise NotImplementedError("sql_value() is not implemented"
                              " for values of type %s" % type(value).__name__)


def sql_create_database(name, template=None):
    """
    Generates::

        CREATE DATABASE {name} [TEMPLATE = {template}]
    """
    # Generates `CREATE DATABASE` statement.
    options = []
    options.append(u"ENCODING = 'UTF-8'")
    if template is not None:
        options.append(u"TEMPLATE = {}".format(sql_name(template)))
    return u"CREATE DATABASE {} WITH {};" \
            .format(sql_name(name), u" ".join(options))


def sql_drop_database(name):
    """
    Generates::

        DROP DATABASE {name}
    """
    return u"DROP DATABASE {};".format(sql_name(name))


def sql_rename_database(name, new_name):
    """
    Generates::

        ALTER DATABASE {name} RENAME TO {new_name}
    """
    return u"ALTER DATABASE {} RENAME TO {};".format(sql_name(name),
                                                     sql_name(new_name))


def sql_select_database(name):
    """
    Generates::

        SELECT TRUE WHERE {name} IN *available databases*
    """
    return u"SELECT TRUE FROM pg_catalog.pg_database AS d" \
            u" WHERE d.datname = {};" \
            .format(sql_value(name))


def sql_comment_on_schema(name, text):
    """
    Generates::

        COMMENT ON SCHEMA {name} IS {text}
    """
    return "COMMENT ON SCHEMA {} IS {};".format(sql_name(name), sql_value(text))


def sql_create_table(name, definitions, is_unlogged=False):
    """
    Generates::

        CREATE [UNLOGGED] TABLE {name} ( {definition}, ... )
    """
    lines = []
    lines.append(u"CREATE{} TABLE {} ("
            .format(u" UNLOGGED" if is_unlogged else u"",
                    sql_name(name)))
    for line in definitions[:-1]:
        lines.append(u"    {},".format(line))
    lines.append(u"    {}".format(definitions[-1]))
    lines.append(u");")
    return u"\n".join(lines)


def sql_drop_table(name):
    """
    Generates::

        DROP TABLE {name}
    """
    return "DROP TABLE {};".format(sql_name(name))


def sql_comment_on_table(name, text):
    """
    Generates::

        COMMENT ON TABLE {name} IS {text}
    """
    return "COMMENT ON TABLE {} IS {};".format(sql_name(name), sql_value(text))


def sql_define_column(name, type_name, is_not_null):
    """
    Generates::

        {name} {type_name} [NOT NULL]
    """
    # Generates column definition for `CREATE TABLE` body.
    return u"{} {}{}" \
            .format(sql_name(name),
                    sql_name(type_name)
                        if not isinstance(type_name, tuple)
                        else u"{}({})"
                                .format(sql_name(type_name[0]),
                                        sql_value(type_name[1:])),
                    u" NOT NULL" if is_not_null else u"")


def sql_add_column(table_name, name, type_name, is_not_null):
    """
    Generates::

        ALTER TABLE {table_name} ADD COLUMN {name} {type_name} [NOT NULL]
    """
    return u"ALTER TABLE {} ADD COLUMN {} {}{};" \
            .format(sql_name(table_name),
                    sql_name(name),
                    sql_name(type_name)
                        if not isinstance(type_name, tuple)
                        else u"{}({})"
                                .format(sql_name(type_name[0]),
                                        sql_value(type_name[1:])),
                    u" NOT NULL" if is_not_null else u"")


def sql_drop_column(table_name, name):
    """
    Generates::

        ALTER TABLE {table_name} DROP COLUMN {name}
    """
    return u"ALTER TABLE {} DROP COLUMN {};" \
            .format(sql_name(table_name),
                    sql_name(name))


def sql_comment_on_column(table_name, name, text):
    """
    Generates::

        COMMENT ON COLUMN {table_name}.{name} IS {text}
    """
    return "COMMENT ON COLUMN {}.{} IS {};" \
            .format(sql_name(table_name),
                    sql_name(name),
                    sql_value(text))


def sql_add_unique_constraint(table_name, name, column_names, is_primary):
    """
    Generates::

        ALTER TABLE {table_name} ADD CONSTRAINT {name}
        { UNIQUE | PRIMARY KEY } ({column_name}, ...)
    """
    return u"ALTER TABLE {} ADD CONSTRAINT {} {} ({});" \
            .format(sql_name(table_name),
                    sql_name(name),
                    u"UNIQUE" if not is_primary else u"PRIMARY KEY",
                    sql_name(column_names))


def sql_add_foreign_key_constraint(table_name, name, column_names,
                                   target_table_name, target_column_names,
                                   on_update=None, on_delete=None):
    """
    Generates::

        ALTER TABLE {table_name} ADD CONSTRAINT {name}
        FOREIGN KEY ({column_name}, ...)
        REFERENCES {target_table_name} ({target_column_name}, ...)
        [ON UPDATE {on_update}] [ON DELETE {on_delete}]
    """
    return u"ALTER TABLE {} ADD CONSTRAINT {}" \
            u" FOREIGN KEY ({}) REFERENCES {} ({}){}{};" \
            .format(sql_name(table_name),
                    sql_name(name),
                    sql_name(column_names),
                    sql_name(target_table_name),
                    sql_name(target_column_names),
                    u" ON UPDATE "+on_update if on_update is not None else u"",
                    u" ON DELETE "+on_delete if on_delete is not None else u"")


def sql_drop_constraint(table_name, name):
    """
    Generates::

        ALTER TABLE {table_name} DROP CONSTRAINT {name}
    """
    return u"ALTER TABLE {} DROP CONSTRAINT {};" \
            .format(sql_name(table_name),
                    sql_name(name))


def sql_comment_on_constraint(table_name, name, text):
    """
    Generates::

        COMMENT ON CONSTRAINT {name} ON {table_name} IS {text}
    """
    return "COMMENT ON CONSTRAINT {} ON {} IS {};" \
            .format(sql_name(name),
                    sql_name(table_name),
                    sql_value(text))


def sql_create_enum_type(name, labels):
    """
    Generates::

        CREATE TYPE {name} AS ENUM ({label}, ...)
    """
    return u"CREATE TYPE {} AS ENUM ({});" \
            .format(sql_name(name),
                    sql_value(labels))


def sql_drop_type(name):
    """
    Generates::

        DROP TYPE {name}
    """
    return u"DROP TYPE {};" \
            .format(sql_name(name))


def sql_comment_on_type(name, text):
    """
    Generates::

        COMMENT ON TYPE {name} IS {text}
    """
    return "COMMENT ON TYPE {} IS {};".format(sql_name(name), sql_value(text))


def sql_create_function(name, types, return_type, language, source):
    """
    Generates::

        CREATE FUNCTION {name}({type}, ...) RETURNS {return_type}
        LANGUAGE {language}
        AS {source}
    """
    return u"CREATE FUNCTION {}({}) RETURNS {} LANGUAGE {} AS {}" \
            .format(sql_name(name),
                    sql_name(types),
                    sql_name(return_type),
                    language,
                    sql_value(source))


def sql_drop_function(name, types):
    """
    Generates::

        DROP FUNCTION {name}({type}, ...)
    """
    return u"DROP FUNCTION {}({})".format(sql_name(name), sql_name(types))


def sql_create_trigger(table_name, name, when, event,
                       function_name, arguments):
    """
    Generates::

        CREATE TRIGGER {name} { BEFORE | AFTER } { INSERT | UPDATE | DELETE }
        ON {table_name}
        FOR EACH ROW EXECUTE PROCEDURE {function_name}({argument}, ...)
    """
    return u"CREATE TRIGGER {} {} {} ON {}" \
            u" FOR EACH ROW EXECUTE PROCEDURE {}({})" \
            .format(sql_name(name), when, event, sql_name(table_name),
                    sql_name(function_name), sql_value(arguments))


def sql_drop_trigger(table_name, name):
    """
    Generates::

        DROP TRIGGER {name} ON {table_name}
    """
    return u"DROP TRIGGER {} ON {}" \
            .format(sql_name(name), sql_name(table_name))


def sql_primary_key_procedure(*parts):
    # Stored procedure for generating the primary key for a new record.
    lines = []
    lines.append(u"\n")
    lines.append(u"BEGIN\n")
    for part in parts:
        for line in part.splitlines():
            lines.append(u"    {}\n".format(line))
    lines.append(u"    RETURN NEW;\n")
    lines.append(u"END;\n")
    return u"".join(lines)


def sql_integer_random_key(table_name, name):
    # Code for generating a random integer key.
    table_name = sql_name(table_name)
    name = sql_name(name)

    lines = []
    lines.append(u"IF NEW.{} IS NULL THEN\n".format(name))
    lines.append(u"    NEW.{} := TRUNC((RANDOM()*999999999) + 1);\n"
                .format(name))
    lines.append(u"END IF;\n")
    return u"".join(lines)


def sql_text_random_key(table_name, name):
    # Code for creating a random text key.
    table_name = sql_name(table_name)
    name = sql_name(name)
    letters = u"ABCDEFGHJKLMNPQRSTUVWXYZ"
    digits = u"0123456789"
    one_letter = u"_letters[1 + TRUNC(RANDOM()*%s)]" % len(letters)
    one_digit = u"_digits[1 + TRUNC(RANDOM()*%s)]" % len(digits)

    lines = []
    lines.append(u"IF NEW.{} IS NULL THEN\n".format(name))
    lines.append(u"    DECLARE\n")
    lines.append(u"        _letters text[] := '{%s}';\n" % u",".join(letters))
    lines.append(u"        _digits text[] := '{%s}';\n" % u",".join(digits))
    lines.append(u"    BEGIN\n")
    lines.append(u"        NEW.{} :=\n".format(name))
    lines.append(u"            %s ||\n" % one_letter)
    lines.append(u"            %s ||\n" % one_digit)
    lines.append(u"            %s ||\n" % one_digit)
    lines.append(u"            %s ||\n" % one_letter)
    lines.append(u"            %s ||\n" % one_digit)
    lines.append(u"            %s ||\n" % one_digit)
    lines.append(u"            %s ||\n" % one_digit)
    lines.append(u"            %s;\n" % one_digit)
    lines.append(u"    END;\n")
    lines.append(u"END IF;\n")
    return u"".join(lines)


def sql_integer_offset_key(table_name, name, basis_names):
    # Code for creating an integer offset key.
    table_name = sql_name(table_name)
    name = sql_name(name)
    basis_names = [sql_name(basis_name) for basis_name in basis_names]
    conditions = [u"{} = NEW.{}".format(basis_name, basis_name)
                  for basis_name in basis_names]

    lines = []
    lines.append(u"IF NEW.{} IS NULL THEN\n".format(name))
    lines.append(u"    DECLARE\n")
    lines.append(u"        _offset int4;\n")
    lines.append(u"    BEGIN\n")
    lines.append(u"        SELECT MAX({}) INTO _offset\n".format(name))
    if conditions:
        lines.append(u"            FROM {}\n".format(table_name))
        lines.append(u"            WHERE %s;\n" % u" AND ".join(conditions))
    else:
        lines.append(u"            FROM {};\n".format(table_name))
    lines.append(u"        NEW.{} := COALESCE(_offset, 0) + 1;\n".format(name))
    lines.append(u"    END;\n")
    lines.append(u"END IF;\n")
    return u"".join(lines)


def sql_text_offset_key(table_name, name, basis_names):
    # Code for creating a text offset key.
    table_name = sql_name(table_name)
    name = sql_name(name)
    basis_names = [sql_name(basis_name) for basis_name in basis_names]
    conditions = [u"{} = NEW.{}".format(basis_name, basis_name)
                  for basis_name in basis_names]
    conditions.append(u"{} ~ '^[0-9]{{3}}$'".format(name))

    lines = []
    lines.append(u"IF NEW.{} IS NULL THEN\n".format(name))
    lines.append(u"    DECLARE\n")
    lines.append(u"        _offset int4;\n")
    lines.append(u"    BEGIN\n")
    lines.append(u"        SELECT CAST(MAX({}) AS int4) INTO _offset\n"
                .format(name))
    lines.append(u"            FROM {}\n".format(table_name))
    lines.append(u"            WHERE %s;\n" % u" AND ".join(conditions))
    lines.append(u"        NEW.{} :="
                 u" TO_CHAR(COALESCE(_offset, 0) + 1, 'FM000');\n"
                .format(name))
    lines.append(u"    END;\n")
    lines.append(u"END IF;\n")
    return u"".join(lines)


def sql_select(table_name, names):
    """
    Generates::

        SELECT {name}, ... FROM {table_name}
    """
    return u"SELECT {}\n    FROM {};" \
            .format(sql_name(names),
                    sql_name(table_name))


def sql_insert(table_name, names, values, returning_names=None):
    """
    Generates::

        INSERT INTO {table_name} ({name}, ...)
        VALUES ({value}, ...)
        RETURNING {returning_name}, ...
    """
    lines = []
    if names:
        lines.append(u"INSERT INTO {} ({})"
                    .format(sql_name(table_name),
                            sql_name(names)))
    else:
        lines.append(u"INSERT INTO {}".format(sql_name(table_name)))
    if values:
        lines.append(u"    VALUES ({})".format(sql_value(values)))
    else:
        lines.append(u"    DEFAULT VALUES")
    if returning_names:
        lines.append(u"    RETURNING {}".format(sql_name(returning_names)))
    return u"\n".join(lines)+u";"


def sql_update(table_name, key_name, key_value, names, values,
               returning_names=None):
    """
    Generates::

        UPDATE {table_name} SET {name} = {value}, ...
        WHERE {key_name} = {key_value}
        RETURNING {returning_name}, ...
    """
    if not (names and values):
        names = [key_name]
        values = [key_value]
    lines = []
    lines.append(u"UPDATE {}".format(sql_name(table_name)))
    lines.append(u"    SET {}"
                .format(u", ".join(u"{} = {}"
                                    .format(sql_name(name),
                                            sql_value(value))
                                   for name, value in zip(names, values))))
    lines.append(u"    WHERE {} = {}"
                .format(sql_name(key_name),
                        sql_value(key_value)))
    if returning_names:
        lines.append(u"    RETURNING {}".format(sql_name(returning_names)))
    return u"\n".join(lines)+u";"


def sql_delete(table_name, key_name, key_value):
    """
    Generates::

        DELETE FROM {table_name}
        WHERE {key_name} = {key_value}
    """
    lines = []
    lines.append(u"DELETE FROM {}".format(sql_name(table_name)))
    lines.append(u"    WHERE {} = {}"
                .format(sql_name(key_name),
                        sql_value(key_value)))
    return u"\n".join(lines)+u";"


