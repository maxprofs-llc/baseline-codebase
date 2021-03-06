import path from "path";

import * as gql from "graphql";
import * as t from "@babel/types";
import generate from "@babel/generator";

const PRELUDE = `
// @flow
// DO NOT EDIT: THIS FILE WAS AUTOGENERATED FROM *.gql DOCUMENTS
`.trimLeft();

/**
 * This is used to handle recursion between definition, null means that we are
 * in progress of generating a type for this definition.
 */
interface GenTypeInProgress {
  value: null | t.Node[];
}

/**
 * Structure used to collect generated types.
 */
interface Context {
  scalars: Map<string, GenTypeInProgress>;
  fragments: Map<string, GenTypeInProgress>;
  operations: Map<string, GenTypeInProgress>;

  schema: gql.GraphQLSchema;

  definitions: {
    fragments: Map<string, gql.DefinitionNode>;
    scalars: Map<string, gql.DefinitionNode>;
  };

  shouldGenerateResourceAPI: boolean;
  shouldGenerateTypesAPI: boolean;
  shouldGenerateVariablesSet: boolean;
}

export interface Config {
  generateResourceAPI?: string;
  generateTypesAPI?: string;
  generateVariablesSet?: boolean;
}

type Promisable<T> = T | Promise<T>;

type PluginOutput =
  | string
  | {
      content: string;
      prepend?: string[];
      append?: string[];
    };

type PluginFunction = (
  schema: gql.GraphQLSchema,
  documents: gql.DocumentNode[],
  config: Config,
  info?: {
    outputFile?: string;
  },
) => Promisable<PluginOutput>;

function emitCollection(
  chunks: string[],
  collection: Map<string, GenTypeInProgress>,
) {
  for (let nodes of collection.values()) {
    for (let node of nodes.value) {
      // TODO(andreypopp): get rid of cast to any, this is because of different
      // versions of @babel/types and @babel/generator, probably.
      chunks.push(generate(node as any).code);
    }
  }
}

function emitNamespaceImport(
  chunks: string[],
  specifier:
    | t.ImportSpecifier
    | t.ImportDefaultSpecifier
    | t.ImportNamespaceSpecifier,
  from: string,
) {
  const node = t.importDeclaration([specifier], t.stringLiteral(from));
  // TODO(andreypopp): get rid of cast to any, this is because of different
  // versions of @babel/types and @babel/generator, probably.
  chunks.push(generate(node as any).code);
}

export const plugin: PluginFunction = (
  schema,
  documents,
  { generateResourceAPI, generateTypesAPI, generateVariablesSet },
  { outputFile },
) => {
  const printedSchema = gql.printSchema(schema);
  const astNode = gql.parse(printedSchema);
  const allAst = gql.concatAST([astNode, ...documents]);

  const imports = [];

  // Build a mapping from names to fragments/scalars so we can generate them
  // lazily as requested.

  let definitions = { fragments: new Map(), scalars: new Map() };
  for (let node of allAst.definitions) {
    switch (node.kind) {
      case "EnumTypeDefinition":
      case "ScalarTypeDefinition":
      case "InputObjectTypeDefinition":
        definitions.scalars.set(node.name.value, node);
        break;
      case "FragmentDefinition": {
        definitions.fragments.set(node.name.value, node);
        break;
      }
      default:
        break;
    }
  }

  if (generateResourceAPI) {
    emitNamespaceImport(
      imports,
      t.importNamespaceSpecifier(resourceAPIIdentifier),
      generateResourceAPI,
    );
  }
  if (generateTypesAPI) {
    emitNamespaceImport(
      imports,
      t.importNamespaceSpecifier(typesAPIIdentifier),
      generateTypesAPI,
    );
  }

  // Visit all OperationDefinition nodes and generate types for them, as we are
  // doing that we will request generation for referenced fragment and scalar
  // types.

  let ctx: Context = {
    scalars: new Map(),
    fragments: new Map(),
    operations: new Map(),
    definitions,
    schema,
    shouldGenerateResourceAPI: generateResourceAPI != null,
    shouldGenerateTypesAPI: generateTypesAPI != null,
    shouldGenerateVariablesSet: generateVariablesSet,
  };

  for (let node of allAst.definitions) {
    switch (node.kind) {
      case "OperationDefinition":
        visitDefinitionNode(ctx, node);
        emitNamespaceImport(
          imports,
          t.importDefaultSpecifier(
            operationTypeName(node.name.value, node.operation),
          ),
          getRelativePath(outputFile, node.loc.source.name),
        );
        break;
      default:
        break;
    }
  }

  // Now emit generates types in order: scalars, fragments, operations,
  // variables

  let chunks = [PRELUDE, imports.join("\n")];

  emitCollection(chunks, ctx.scalars);
  emitCollection(chunks, ctx.fragments);
  emitCollection(chunks, ctx.operations);

  return chunks.join("\n\n");
};

function visitDefinitionNode(ctx: Context, node: gql.DefinitionNode) {
  switch (node.kind) {
    case "OperationDefinition": {
      if (ctx.operations.has(node.name.value)) {
        break;
      }
      ctx.operations.set(node.name.value, { value: null });
      let type: gql.GraphQLObjectType;
      switch (node.operation) {
        case "query":
          type = ctx.schema.getQueryType();
          break;
        case "mutation":
          type = ctx.schema.getMutationType();
          break;
        case "subscription":
          break;
      }
      let value = [
        generateVariablesDeclaration(ctx, node),
        generateResultDeclaration(ctx, node, type),
      ];
      if (ctx.shouldGenerateVariablesSet) {
        value.push(generateVariablesSet(node));
      }
      if (ctx.shouldGenerateResourceAPI) {
        value.push(generateResourceAPI(node));
      }
      ctx.operations.set(node.name.value, { value });
      break;
    }
    case "FragmentDefinition": {
      if (ctx.fragments.has(node.name.value)) {
        break;
      }
      ctx.fragments.set(node.name.value, { value: null });
      let type = ctx.schema.getType(node.typeCondition.name.value);
      assert(
        type instanceof gql.GraphQLObjectType,
        "Expected GraphQLObjectType",
      );
      let value = t.exportNamedDeclaration(
        t.typeAlias(
          fragmentTypeName(node.name.value),
          null,
          printSelectionSet(node.selectionSet, type, ctx),
        ),
        [],
      );
      ctx.fragments.set(node.name.value, { value: [value] });
      break;
    }
    case "ScalarTypeDefinition": {
      if (ctx.scalars.has(node.name.value)) {
        break;
      }
      ctx.scalars.set(node.name.value, { value: null });
      let value = t.exportNamedDeclaration(
        t.typeAlias(
          scalarTypeName(node.name.value),
          null,
          getTypeAnnotation(ctx, node.name.value),
        ),
        [],
      );
      ctx.scalars.set(node.name.value, { value: [value] });
      break;
    }
    case "EnumTypeDefinition": {
      if (ctx.scalars.has(node.name.value)) {
        break;
      }
      ctx.scalars.set(node.name.value, { value: null });
      let value = t.exportNamedDeclaration(
        t.typeAlias(
          scalarTypeName(node.name.value),
          null,
          t.unionTypeAnnotation(
            node.values.map(value =>
              t.stringLiteralTypeAnnotation(value.name.value),
            ),
          ),
        ),
        [],
      );
      ctx.scalars.set(node.name.value, { value: [value] });
      break;
    }
    case "InputObjectTypeDefinition": {
      if (ctx.scalars.has(node.name.value)) {
        break;
      }
      ctx.scalars.set(node.name.value, { value: null });
      let value = t.exportNamedDeclaration(
        t.typeAlias(
          scalarTypeName(node.name.value),
          null,
          t.objectTypeAnnotation(
            node.fields.map(field => ({
              ...t.objectTypeProperty(
                t.identifier(field.name.value),
                printVariableType(ctx, field.type),
              ),
              optional: field.type.kind !== "NonNullType",
            })),
            null,
            null,
            null,
            true,
          ),
        ),
      );
      ctx.scalars.set(node.name.value, { value: [value] });
      break;
    }
    default: {
      break;
    }
  }
}

function generateVariablesDeclaration(
  ctx: Context,
  { name: { value: name }, variableDefinitions }: gql.OperationDefinitionNode,
) {
  return t.exportNamedDeclaration(
    t.typeAlias(
      operationVariablesTypeName(name),
      null,
      printVariables(ctx, variableDefinitions),
    ),
    [],
  );
}

function generateVariablesSet({
  name: { value: name },
  variableDefinitions,
}: gql.OperationDefinitionNode) {
  return t.exportNamedDeclaration(
    t.variableDeclaration("let", [
      t.variableDeclarator(operationVariablesSetName(name), {
        ...t.newExpression(t.identifier("Set"), [
          t.arrayExpression(
            variableDefinitions.map(varDef =>
              t.stringLiteral(varDef.variable.name.value),
            ),
          ),
        ]),
        typeArguments: t.typeParameterInstantiation([t.stringTypeAnnotation()]),
      }),
    ]),
    [],
  );
}

function generateResultDeclaration(
  ctx: Context,
  { name: { value: name }, selectionSet }: gql.OperationDefinitionNode,
  type: gql.GraphQLObjectType,
) {
  return t.exportNamedDeclaration(
    t.typeAlias(
      operationResultTypeName(name),
      null,
      printSelectionSet(selectionSet, type, ctx),
    ),
    [],
  );
}

function generateResourceAPI({
  name: { value: name },
  operation,
}: gql.OperationDefinitionNode) {
  return t.exportNamedDeclaration(
    t.variableDeclaration("let", [
      t.variableDeclarator(
        t.identifier(name),
        Object.assign(
          t.callExpression(
            t.memberExpression(
              resourceAPIIdentifier,
              getDefinePropertyName(operation),
            ),
            [
              t.objectExpression([
                t.objectProperty(
                  t.identifier(operation),
                  operationTypeName(name, operation),
                ),
              ]),
            ],
          ),
          {
            typeArguments: t.typeParameterInstantiation([
              t.genericTypeAnnotation(operationVariablesTypeName(name)),
              t.genericTypeAnnotation(operationResultTypeName(name)),
            ]),
          },
        ),
      ),
    ]),
    [],
  );
}

function printVariables(
  ctx: Context,
  nodes: readonly gql.VariableDefinitionNode[],
) {
  let properties = [];
  for (let node of nodes) {
    properties.push(
      Object.assign(
        t.objectTypeProperty(
          t.identifier(node.variable.name.value),
          printVariableType(ctx, node.type),
        ),
        {
          optional: node.type.kind !== "NonNullType",
        },
      ),
    );
  }
  return t.objectTypeAnnotation(properties, null, null, null, true);
}

function printVariableType(ctx: Context, type: gql.TypeNode): t.FlowType {
  switch (type.kind) {
    case "NamedType":
      return t.nullableTypeAnnotation(printScalarType(ctx, type.name.value));
    case "ListType":
      return t.nullableTypeAnnotation(
        t.genericTypeAnnotation(
          t.identifier("Array"),
          t.typeParameterInstantiation([printVariableType(ctx, type.type)]),
        ),
      );
    case "NonNullType":
      switch (type.type.kind) {
        case "NamedType":
          return printScalarType(ctx, type.type.name.value);
        case "ListType":
          return t.genericTypeAnnotation(
            t.identifier("Array"),
            t.typeParameterInstantiation([
              printVariableType(ctx, type.type.type),
            ]),
          );
      }
    default:
      exhaustiveCheck(type);
  }
}

function printSelectionSet(
  node: gql.SelectionSetNode,
  type: gql.GraphQLObjectType,
  ctx: Context,
): t.FlowType {
  let fields = type.getFields();
  let properties = [];

  for (let f of node.selections) {
    switch (f.kind) {
      case "FragmentSpread": {
        let fnode = ctx.definitions.fragments.get(f.name.value);
        assert(fnode != null, `Unknown fragment referenced "${f.name.value}"`);
        visitDefinitionNode(ctx, fnode);
        properties.push(
          t.objectTypeSpreadProperty(
            t.genericTypeAnnotation(fragmentTypeName(f.name.value)),
          ),
        );
        break;
      }
      case "Field": {
        let field = fields[f.name.value];
        properties.push(
          t.objectTypeProperty(
            t.identifier(f.alias ? f.alias.value : f.name.value),
            printFieldOutputType(ctx, field.type, f, true),
          ),
        );
        break;
      }
      case "InlineFragment":
        break;
      default:
        exhaustiveCheck(f);
    }
  }
  return t.objectTypeAnnotation(properties, null, null, null, true);
}

function printFieldOutputType(ctx: Context, type, node, nullable): t.FlowType {
  let typeNode: t.FlowType;
  if (type instanceof gql.GraphQLScalarType) {
    typeNode = printScalarType(ctx, type.name);
  } else if (type instanceof gql.GraphQLObjectType) {
    typeNode = printSelectionSet(node.selectionSet, type, ctx);
  } else if (type instanceof gql.GraphQLEnumType) {
    typeNode = printScalarType(ctx, type.name);
  } else if (type instanceof gql.GraphQLNonNull) {
    typeNode = printFieldOutputType(ctx, type.ofType, node, false);
    return typeNode;
  } else if (type instanceof gql.GraphQLList) {
    typeNode = printFieldOutputType(ctx, type.ofType, node, nullable);
    typeNode = t.genericTypeAnnotation(
      t.identifier("Array"),
      t.typeParameterInstantiation([typeNode]),
    );
  } else {
    console.log(type);
    throw new Error(`Unsupported type: ${type}`);
  }
  if (nullable) {
    typeNode = t.nullableTypeAnnotation(typeNode);
  }
  return typeNode;
}

function printScalarType(ctx: Context, name: string): t.FlowType {
  switch (name) {
    case "String":
      return t.stringTypeAnnotation();
    case "Boolean":
      return t.booleanTypeAnnotation();
    case "Int":
      return t.numberTypeAnnotation();
    case "Float":
      return t.numberTypeAnnotation();
    case "Date":
      return t.stringTypeAnnotation();
    case "Datetime":
      return t.stringTypeAnnotation();
    case "Time":
      return t.stringTypeAnnotation();
    default: {
      let tnode = ctx.definitions.scalars.get(name);
      assert(tnode != null, `Unknown scalar referenced "${name}"`);
      visitDefinitionNode(ctx, tnode);
      return t.genericTypeAnnotation(scalarTypeName(name));
    }
  }
}

function getTypeAnnotation(ctx: Context, name: string): t.FlowType {
  switch (name) {
    case "JSON":
      // We emit custom JSON type here.
      return t.nullableTypeAnnotation(
        t.unionTypeAnnotation([
          t.stringTypeAnnotation(),
          t.numberTypeAnnotation(),
          t.booleanTypeAnnotation(),
          t.genericTypeAnnotation(
            t.identifier("Array"),
            t.typeParameterInstantiation([
              t.genericTypeAnnotation(t.identifier("JSON")),
            ]),
          ),
          t.genericTypeAnnotation(
            t.identifier("$ReadOnlyArray"),
            t.typeParameterInstantiation([
              t.genericTypeAnnotation(t.identifier("JSON")),
            ]),
          ),
          t.objectTypeAnnotation([
            t.objectTypeProperty(
              t.identifier("[key: string]"),
              t.genericTypeAnnotation(t.identifier("JSON")),
            ),
          ]),
          t.objectTypeAnnotation([
            t.objectTypeProperty(
              t.identifier("+[key: string]"),
              t.genericTypeAnnotation(t.identifier("JSON")),
            ),
          ]),
        ]),
      );
    default: {
      if (ctx.shouldGenerateTypesAPI) {
        return t.genericTypeAnnotation(
          t.qualifiedTypeIdentifier(t.identifier(name), typesAPIIdentifier),
        );
      } else {
        return t.mixedTypeAnnotation();
      }
    }
  }
}

let resourceAPIIdentifier = t.identifier("__resource");
let typesAPIIdentifier = t.identifier("__types");

function operationTypeName(name: string, operation: string) {
  const suffix = operation.charAt(0).toUpperCase() + operation.slice(1);
  return t.identifier(name + suffix);
}

function operationResultTypeName(name: string) {
  return t.identifier(`${name}Result`);
}

function operationVariablesTypeName(name: string) {
  return t.identifier(`${name}Variables`);
}

function operationVariablesSetName(name: string) {
  return t.identifier(`${name}VariablesSet`);
}

function fragmentTypeName(name: string) {
  return t.identifier(`${name}Fragment`);
}

function scalarTypeName(name: string) {
  return t.identifier(`${name}`);
}

function exhaustiveCheck(param: never): never {
  throw new Error("should not reach here");
}

function assert(value: unknown, message: string): asserts value {
  if (!value) {
    throw new Error(`assertion failed: ${message}`);
  }
}

function getRelativePath(from: string, to: string) {
  const fromFilePath = path.parse(from);
  const toFilePath = path.parse(to);
  const relativePath = path.relative(fromFilePath.dir, toFilePath.dir);
  const pathPrefix = relativePath.charAt(0) !== "." ? "./" : "";
  return pathPrefix + path.join(relativePath, toFilePath.base);
}

function getDefinePropertyName(operation: gql.OperationTypeNode) {
  switch (operation) {
    case "query":
      return t.identifier("defineQuery");
    case "mutation":
      return t.identifier("defineMutation");
    case "subscription":
      return t.identifier("defineSubscription");
  }
}
