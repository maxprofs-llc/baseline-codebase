#
# Copyright (c) 2013, Prometheus Research, LLC
#


from .image import CatalogImage


def introspect(connection):
    """
    Returns a catalog image that reflects the structure of the database.
    """
    cursor = connection.cursor()

    catalog = CatalogImage()

    # Extract schemas.
    cursor.execute("""
        SELECT n.oid, n.nspname
        FROM pg_catalog.pg_namespace n
        ORDER BY n.nspname
    """)
    schema_by_oid = {}
    for oid, nspname in cursor.fetchall():
        schema = catalog.add_schema(nspname)
        schema_by_oid[oid] = schema

    # Extract ENUM labels.
    labels_by_oid = {}
    cursor.execute("""
        SELECT e.enumtypid, e.enumlabel
        FROM pg_catalog.pg_enum e
        ORDER BY e.enumtypid, e.enumsortorder, e.oid
    """)
    for enumtypid, enumlabel in cursor.fetchall():
        labels_by_oid.setdefault(enumtypid, []).append(enumlabel)

    # Extract data types.
    type_by_oid = {}
    cursor.execute("""
        SELECT t.oid, t.typnamespace, t.typname, t.typtype,
               t.typbasetype, t.typlen, t.typtypmod, t.typdefault
        FROM pg_catalog.pg_type t
        ORDER BY t.typnamespace, t.typname
    """)
    for (oid, typnamespace, typname, typtype,
         typbasetype, typlen, typtypmod, typdefault) in cursor.fetchall():
        schema = schema_by_oid[typnamespace]
        if typtype == 'e':
            labels = labels_by_oid[oid]
            type = schema.add_enum_type(typname, labels)
        else:
            type = schema.add_type(typname)
        type_by_oid[oid] = type

    # Extract tables.
    table_by_oid = {}
    cursor.execute("""
        SELECT c.oid, c.relnamespace, c.relname
        FROM pg_catalog.pg_class c
        WHERE c.relkind IN ('r', 'v') AND
              HAS_TABLE_PRIVILEGE(c.oid, 'SELECT')
        ORDER BY c.relnamespace, c.relname
    """)
    for oid, relnamespace, relname in cursor.fetchall():
        if relnamespace not in schema_by_oid:
            continue
        schema = schema_by_oid[relnamespace]
        table = schema.add_table(relname)
        table_by_oid[oid] = table

    # Extract columns.
    column_by_num = {}
    cursor.execute("""
        SELECT a.attrelid, a.attnum, a.attname, a.atttypid, a.atttypmod,
               a.attnotnull, a.atthasdef, a.attisdropped
        FROM pg_catalog.pg_attribute a
        ORDER BY a.attrelid, a.attnum
    """)
    for (attrelid, attnum, attname, atttypid,
         atttypmod, attnotnull, atthasdef, attisdropped) in cursor.fetchall():
        if attisdropped:
            continue
        if attname in ['tableoid', 'cmax', 'xmax', 'cmin', 'xmin', 'ctid']:
            continue
        if attrelid not in table_by_oid:
            continue
        table = table_by_oid[attrelid]
        type = type_by_oid[atttypid]
        is_not_null = bool(attnotnull)
        column = table.add_column(attname, type, is_not_null)
        column_by_num[attrelid, attnum] = column

    # Extract constraints.
    cursor.execute("""
        SELECT c.conname, c.contype, c.confmatchtype,
               c.conrelid, c.conkey, c.confrelid, c.confkey
        FROM pg_catalog.pg_constraint c
        WHERE c.contype IN ('p', 'u', 'f')
        ORDER BY c.oid
    """)
    for (conname, contype, confmatchtype,
            conrelid, conkey, confrelid, confkey) in cursor.fetchall():
        if conrelid not in table_by_oid:
            continue
        table = table_by_oid[conrelid]
        if not all((conrelid, num) in column_by_num
                   for num in conkey):
            continue
        columns = [column_by_num[conrelid, num] for num in conkey]
        if contype in ('p', 'u'):
            is_primary = (contype == 'p')
            table.add_unique_key(conname, columns, is_primary)
        elif contype == 'f':
            if confrelid not in table_by_oid:
                continue
            target_table = table_by_oid[confrelid]
            if not all((confrelid, num) in column_by_num for num in confkey):
                continue
            target_columns = [column_by_num[confrelid, num] for num in confkey]
            table.add_foreign_key(conname, columns, target_table, target_columns)

    return catalog


