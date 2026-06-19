/**
 * Power BI Schema Validator
 *
 * Deterministic star-schema and DAX quality checks.
 * Call validate(schema) before generating any PBIP with pbir-generator.js.
 *
 * Schema shape:
 * {
 *   tables: [
 *     {
 *       name: string,
 *       type: "fact" | "dimension" | "date" | "measures" | "bridge",
 *       isDateTable?: boolean,       // true for the date dimension
 *       dateColumn?: string,         // name of the Date column in date table
 *       columns: [
 *         {
 *           name: string,
 *           dataType: "string" | "int64" | "decimal" | "date" | "datetime" | "boolean",
 *           isHidden?: boolean,
 *         }
 *       ],
 *       measures?: [
 *         { name: string, expression: string, formatString?: string }
 *       ]
 *     }
 *   ],
 *   relationships: [
 *     {
 *       fromTable: string,           // many side
 *       fromColumn: string,
 *       toTable: string,             // one side
 *       toColumn: string,
 *       cardinality: "many-to-one" | "one-to-one" | "many-to-many",
 *       crossFilterDirection: "single" | "both",
 *       isActive?: boolean,          // defaults true
 *     }
 *   ]
 * }
 *
 * Returns:
 * {
 *   passed: boolean,
 *   errorCount: number,
 *   warningCount: number,
 *   errors:   [{ code, message, table?, column?, relationship?, measure? }],
 *   warnings: [{ code, message, table?, column?, relationship?, measure? }],
 *   summary: string,
 * }
 */

'use strict';

// ── Helpers ────────────────────────────────────────────────────────────────

function tablesByType(schema, type) {
  return schema.tables.filter(t => t.type === type);
}

function findTable(schema, name) {
  return schema.tables.find(t => t.name === name);
}

function findColumn(table, name) {
  return (table.columns || []).find(c => c.name === name);
}

function hasDateLikeColumn(table) {
  return (table.columns || []).some(c =>
    c.dataType === 'date' || c.dataType === 'datetime' ||
    /date/i.test(c.name)
  );
}

// ── Individual checks ──────────────────────────────────────────────────────

function checkFlatTable(schema, errors) {
  const nonMeasureTables = schema.tables.filter(t => t.type !== 'measures');
  if (nonMeasureTables.length === 1) {
    errors.push({
      code: 'FLAT_TABLE',
      message:
        `Only one table ('${nonMeasureTables[0].name}') — this is a flat/denormalized design. ` +
        `Split into a fact table and dimension tables to build a proper star schema.`,
      table: nonMeasureTables[0].name,
    });
  }
}

function checkNoFactTable(schema, errors) {
  const nonMeasureTables = schema.tables.filter(t => t.type !== 'measures');
  if (nonMeasureTables.length > 1 && tablesByType(schema, 'fact').length === 0) {
    errors.push({
      code: 'NO_FACT_TABLE',
      message:
        `No table is marked type 'fact'. A star schema requires at least one central fact table ` +
        `containing measurable, additive values (revenue, quantity, duration, etc.).`,
    });
  }
}

function checkNoDateDimension(schema, errors) {
  const dateTables = schema.tables.filter(t => t.type === 'date' || t.isDateTable);
  const tablesNeedingDates = schema.tables.filter(
    t => t.type !== 'measures' && hasDateLikeColumn(t)
  );
  if (tablesNeedingDates.length > 0 && dateTables.length === 0) {
    errors.push({
      code: 'NO_DATE_DIMENSION',
      message:
        `Date/datetime columns detected but no date dimension table exists. ` +
        `Create a dedicated DimDate table, mark it as a date table, and relate all date columns to it. ` +
        `Never rely on Power BI's auto date/time feature in production models.`,
    });
  }
}

function checkRelationships(schema, errors, warnings) {
  if (!schema.relationships || schema.relationships.length === 0) return;

  const dimNames = tablesByType(schema, 'dimension').map(t => t.name);

  schema.relationships.forEach(rel => {
    const fromTable = findTable(schema, rel.fromTable);
    const toTable   = findTable(schema, rel.toTable);

    // Many-to-many
    if (rel.cardinality === 'many-to-many') {
      errors.push({
        code: 'MANY_TO_MANY',
        message:
          `Relationship ${rel.fromTable}[${rel.fromColumn}] → ${rel.toTable}[${rel.toColumn}] ` +
          `is many-to-many. Use a bridge/junction table and two many-to-one relationships instead.`,
        relationship: rel,
      });
    }

    // Bidirectional cross-filter
    if (rel.crossFilterDirection === 'both') {
      errors.push({
        code: 'BIDIRECTIONAL_FILTER',
        message:
          `Relationship ${rel.fromTable} → ${rel.toTable} uses bidirectional cross-filter. ` +
          `This causes filter ambiguity, unpredictable results, and performance degradation. ` +
          `Use single-direction filtering and CROSSFILTER() / USERELATIONSHIP() in DAX when needed.`,
        relationship: rel,
      });
    }

    // String/text relationship keys
    if (fromTable) {
      const col = findColumn(fromTable, rel.fromColumn);
      if (col && col.dataType === 'string') {
        errors.push({
          code: 'STRING_RELATIONSHIP_KEY',
          message:
            `${rel.fromTable}[${rel.fromColumn}] is a string column used as a relationship key. ` +
            `Use integer surrogate keys for all relationships — strings are slow and error-prone.`,
          table: rel.fromTable,
          column: rel.fromColumn,
        });
      }
    }
    if (toTable) {
      const col = findColumn(toTable, rel.toColumn);
      if (col && col.dataType === 'string') {
        errors.push({
          code: 'STRING_RELATIONSHIP_KEY',
          message:
            `${rel.toTable}[${rel.toColumn}] is a string column used as a relationship key. ` +
            `Use integer surrogate keys for all relationships — strings are slow and error-prone.`,
          table: rel.toTable,
          column: rel.toColumn,
        });
      }
    }

    // Snowflake: dimension → dimension relationship
    if (dimNames.includes(rel.fromTable) && dimNames.includes(rel.toTable)) {
      warnings.push({
        code: 'SNOWFLAKE_SCHEMA',
        message:
          `Dimension '${rel.fromTable}' has a relationship to dimension '${rel.toTable}'. ` +
          `This creates a snowflake schema. Denormalize into a single flattened dimension unless ` +
          `table size makes denormalization impractical.`,
        relationship: rel,
      });
    }
  });
}

function checkFactTableTextColumns(schema, errors) {
  tablesByType(schema, 'fact').forEach(fact => {
    const suspectCols = (fact.columns || []).filter(c =>
      c.dataType === 'string' &&
      !/key$/i.test(c.name) &&
      !/_key$/i.test(c.name) &&
      !/_id$/i.test(c.name) &&
      !c.isHidden
    );
    if (suspectCols.length > 0) {
      errors.push({
        code: 'TEXT_IN_FACT',
        message:
          `Fact table '${fact.name}' contains text columns that likely belong in dimensions: ` +
          suspectCols.map(c => c.name).join(', ') + `. ` +
          `Move descriptive text to dimension tables and join via surrogate key.`,
        table: fact.name,
        columns: suspectCols.map(c => c.name),
      });
    }
  });
}

function checkMeasures(schema, errors, warnings) {
  const aggInColPattern   = /^=?\s*(SUM|AVERAGE|MAX|MIN|COUNT|COUNTROWS)\s*\(/i;
  const countPattern      = /\bCOUNT\s*\(\s*[^)]+\)/i;
  const countRowsPattern  = /\bCOUNTROWS\s*\(/i;
  const hardcodedPattern  = /[=<>!]=?\s*\d{4,}/;

  schema.tables.forEach(table => {
    // Aggregation logic in calculated columns (heuristic: column names look like measures)
    (table.columns || []).forEach(col => {
      if (col.expression && aggInColPattern.test(col.expression)) {
        errors.push({
          code: 'AGGREGATION_IN_COLUMN',
          message:
            `Column '${table.name}[${col.name}]' contains aggregation logic (${col.expression.trim().slice(0, 40)}…). ` +
            `Aggregations belong in measures, not calculated columns — columns are computed row-by-row ` +
            `and cannot adapt to filter context.`,
          table: table.name,
          column: col.name,
        });
      }
    });

    // COUNT() instead of COUNTROWS() / DISTINCTCOUNT()
    (table.measures || []).forEach(m => {
      if (countPattern.test(m.expression) && !countRowsPattern.test(m.expression)) {
        errors.push({
          code: 'COUNT_NOT_COUNTROWS',
          message:
            `Measure '${table.name}[${m.name}]' uses COUNT(column) — use COUNTROWS(table) to count ` +
            `rows or DISTINCTCOUNT(column) for unique values. COUNT() is the Excel habit; DAX has better options.`,
          table: table.name,
          measure: m.name,
        });
      }

      // Hardcoded thresholds
      if (hardcodedPattern.test(m.expression)) {
        warnings.push({
          code: 'HARDCODED_VALUE',
          message:
            `Measure '${table.name}[${m.name}]' may contain a hardcoded numeric threshold. ` +
            `Consider a parameter table so business users can adjust values without DAX edits.`,
          table: table.name,
          measure: m.name,
        });
      }
    });
  });
}

function checkHiddenForeignKeys(schema, warnings) {
  tablesByType(schema, 'fact').forEach(fact => {
    (fact.columns || [])
      .filter(c => /key$/i.test(c.name) || /_key$/i.test(c.name) || /_id$/i.test(c.name))
      .filter(c => !c.isHidden)
      .forEach(col => {
        warnings.push({
          code: 'FK_NOT_HIDDEN',
          message:
            `Foreign key '${fact.name}[${col.name}]' is visible to report users. ` +
            `Set isHidden: true — surrogate keys have no business meaning in a report.`,
          table: fact.name,
          column: col.name,
        });
      });
  });
}

function checkScatteredMeasures(schema, warnings) {
  const tablesWithMeasures = schema.tables.filter(
    t => t.type !== 'measures' && t.measures && t.measures.length > 0
  );
  if (tablesWithMeasures.length > 2) {
    warnings.push({
      code: 'SCATTERED_MEASURES',
      message:
        `Measures are spread across ${tablesWithMeasures.length} tables ` +
        `(${tablesWithMeasures.map(t => t.name).join(', ')}). ` +
        `Consolidate into a dedicated _Measures table so users have one place to find calculations.`,
    });
  }
}

function checkMixedGranularity(schema, warnings) {
  // Heuristic: fact table has both header-like and line-like columns
  tablesByType(schema, 'fact').forEach(fact => {
    const names = (fact.columns || []).map(c => c.name.toLowerCase());
    const hasHeader = names.some(n => /order|invoice|contract|header/i.test(n));
    const hasLine   = names.some(n => /line|item|detail|row/i.test(n));
    if (hasHeader && hasLine) {
      warnings.push({
        code: 'MIXED_GRANULARITY',
        message:
          `Fact table '${fact.name}' may mix header-level and line-level data. ` +
          `Ensure all rows represent the same grain — split into separate fact tables if needed.`,
        table: fact.name,
      });
    }
  });
}

// ── Main entry point ───────────────────────────────────────────────────────

function validate(schema) {
  const errors   = [];
  const warnings = [];

  checkFlatTable(schema, errors);
  checkNoFactTable(schema, errors);
  checkNoDateDimension(schema, errors);
  checkRelationships(schema, errors, warnings);
  checkFactTableTextColumns(schema, errors);
  checkMeasures(schema, errors, warnings);
  checkHiddenForeignKeys(schema, warnings);
  checkScatteredMeasures(schema, warnings);
  checkMixedGranularity(schema, warnings);

  const passed = errors.length === 0;
  const lines  = [];
  if (errors.length)   lines.push(`${errors.length} error(s):`  , ...errors.map(e   => `  ✗ [${e.code}] ${e.message}`));
  if (warnings.length) lines.push(`${warnings.length} warning(s):`, ...warnings.map(w => `  ⚠ [${w.code}] ${w.message}`));
  if (passed && !warnings.length) lines.push('✓ Schema passed all checks.');
  else if (passed) lines.push('✓ No blocking errors — review warnings before proceeding.');

  return { passed, errorCount: errors.length, warningCount: warnings.length, errors, warnings, summary: lines.join('\n') };
}

module.exports = { validate };
