/**
 * PBIR Report Generator
 *
 * Generates a complete Power BI Project (PBIP) from a config object.
 *
 * Key format rules discovered from Desktop v2.155.xxx (June 2026):
 *  - Page IDs must be bare 20 lowercase hex chars — ReportSection+24hex is silently rejected
 *  - Visual IDs must be bare 20 lowercase hex chars
 *  - All JSON files must be UTF-8 without BOM
 *  - Visual field expressions: use Measure{} for named measures, Column{} for columns
 *
 * Usage:
 *   const { generate } = require('./pbir-generator');
 *   generate(config);
 *
 * Config shape:
 * {
 *   outputDir: string,           // root folder, e.g. "C:\\Reports\\MyReport"
 *   reportName: string,          // e.g. "MyReport"
 *   semanticModel: {
 *     entity: string,            // table name in the model
 *     source: "inline" | "path",
 *     // if source === "inline":
 *     columns: [{ name, dataType }],   // dataType: "string" | "int64" | "double"
 *     measures: [{ name, expression, formatString? }],
 *     rows: Array<Array<any>>,
 *     // if source === "path":
 *     modelPath: string,         // relative path to existing .SemanticModel folder
 *   },
 *   pages: [
 *     {
 *       name: string,            // display name
 *       visuals: [
 *         // Clustered column chart
 *         { type: "clusteredColumnChart", category: string, measure: string, position?: {...} }
 *         // Card (multi-value)
 *         { type: "cardVisual", measures: string[], position?: {...} }
 *         // Table
 *         { type: "tableEx", columns: string[], position?: {...} }
 *       ]
 *     }
 *   ]
 * }
 */

'use strict';

const fs   = require('fs');
const path = require('path');
const crypto = require('crypto');

// ── Utilities ──────────────────────────────────────────────────────────────

function hex20() {
  return crypto.randomBytes(10).toString('hex');  // 20 hex chars
}

const utf8NoBom = { encoding: 'utf8' };

function mkdirp(dir) {
  fs.mkdirSync(dir, { recursive: true });
}

function writeJson(filePath, obj) {
  mkdirp(path.dirname(filePath));
  fs.writeFileSync(filePath, JSON.stringify(obj, null, 2), utf8NoBom);
}

// ── Field expression builders ──────────────────────────────────────────────

function sourceRef(entity) {
  return { SourceRef: { Entity: entity } };
}

function measureField(entity, property) {
  return { Measure: { Expression: sourceRef(entity), Property: property } };
}

function columnField(entity, property) {
  return { Column: { Expression: sourceRef(entity), Property: property } };
}

function measureProjection(entity, prop) {
  return {
    field: measureField(entity, prop),
    queryRef: `${entity}.${prop}`,
    nativeQueryRef: prop,
  };
}

function columnProjection(entity, prop, active = false) {
  const p = {
    field: columnField(entity, prop),
    queryRef: `${entity}.${prop}`,
    nativeQueryRef: prop,
  };
  if (active) p.active = true;
  return p;
}

// ── Visual builders ────────────────────────────────────────────────────────

const VIS_SCHEMA =
  'https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.9.0/schema.json';

function defaultPos(overrides, defaults) {
  return Object.assign({}, defaults, overrides || {});
}

function buildClusteredColumnChart(entity, cfg, name) {
  const pos = defaultPos(cfg.position, { x: 20, y: 20, z: 1000, height: 500, width: 600, tabOrder: 1000 });
  return {
    $schema: VIS_SCHEMA,
    name,
    position: pos,
    visual: {
      visualType: 'clusteredColumnChart',
      query: {
        queryState: {
          Category: { projections: [columnProjection(entity, cfg.category, true)] },
          Y: { projections: [measureProjection(entity, cfg.measure)] },
        },
      },
    },
  };
}

function buildCardVisual(entity, cfg, name) {
  const pos = defaultPos(cfg.position, { x: 20, y: 20, z: 1000, height: 120, width: 1240, tabOrder: 1000 });
  return {
    $schema: VIS_SCHEMA,
    name,
    position: pos,
    visual: {
      visualType: 'cardVisual',
      query: {
        queryState: {
          Data: { projections: cfg.measures.map(m => measureProjection(entity, m)) },
        },
      },
    },
  };
}

function buildTableEx(entity, cfg, name) {
  const pos = defaultPos(cfg.position, { x: 20, y: 20, z: 1000, height: 680, width: 1240, tabOrder: 1000 });
  return {
    $schema: VIS_SCHEMA,
    name,
    position: pos,
    visual: {
      visualType: 'tableEx',
      query: {
        queryState: {
          Values: { projections: cfg.columns.map(c => columnProjection(entity, c)) },
        },
      },
    },
  };
}

function buildVisual(entity, cfg) {
  const name = hex20();
  switch (cfg.type) {
    case 'clusteredColumnChart': return buildClusteredColumnChart(entity, cfg, name);
    case 'cardVisual':           return buildCardVisual(entity, cfg, name);
    case 'tableEx':              return buildTableEx(entity, cfg, name);
    default: throw new Error(`Unknown visual type: ${cfg.type}`);
  }
}

// ── Semantic model builder ────────────────────────────────────────────────

function buildModelBim(entity, sm) {
  const typeMap = { string: 'text', int64: 'Int64.Type', double: 'Double.Type', number: 'Double.Type' };
  const colDefs = sm.columns.map(c => `${c.name} = ${typeMap[c.dataType] || 'text'}`).join(', ');
  const rowLines = sm.rows.map(row => {
    const vals = row.map(v => typeof v === 'string' ? `"${v}"` : v).join(', ');
    return `            {${vals}}`;
  });

  const mExpr = [
    'let',
    `    Source = #table(`,
    `        type table [${colDefs}],`,
    '        {',
    rowLines.join(',\n'),
    '        }',
    '    )',
    'in',
    '    Source',
  ];

  const bimColumns = sm.columns.map(c => ({
    name: c.name,
    dataType: c.dataType === 'string' ? 'string' : 'int64',
    sourceColumn: c.name,
  }));

  const bimMeasures = (sm.measures || []).map(m => ({
    name: m.name,
    expression: m.expression,
    ...(m.formatString ? { formatString: m.formatString } : {}),
  }));

  return {
    compatibilityLevel: 1567,
    model: {
      culture: 'en-US',
      dataAccessOptions: { legacyRedirects: true, returnErrorValuesAsNull: true },
      defaultPowerBIDataSourceVersion: 'powerBI_V3',
      sourceQueryCulture: 'en-US',
      tables: [{
        name: entity,
        columns: bimColumns,
        measures: bimMeasures,
        partitions: [{
          name: entity,
          dataView: 'full',
          source: { type: 'm', expression: mExpr },
        }],
      }],
      relationships: [],
      annotations: [{ name: 'PBIDesktopVersion', value: '2.131.901.0 (24.07)' }],
    },
  };
}

// ── Main generate function ─────────────────────────────────────────────────

const PLATFORM_SCHEMA =
  'https://developer.microsoft.com/json-schemas/fabric/gitIntegration/platformProperties/2.0.0/schema.json';
const PAGE_SCHEMA =
  'https://developer.microsoft.com/json-schemas/fabric/item/report/definition/page/2.1.0/schema.json';
const REPORT_SCHEMA =
  'https://developer.microsoft.com/json-schemas/fabric/item/report/definition/report/3.3.0/schema.json';
const PAGES_SCHEMA =
  'https://developer.microsoft.com/json-schemas/fabric/item/report/definition/pagesMetadata/1.0.0/schema.json';

function generate(config) {
  const { outputDir, reportName, semanticModel: sm, pages } = config;
  const entity = sm.entity;

  // ── Semantic Model ────────────────────────────────────────────────────
  const smDir = path.join(outputDir, `${reportName}.SemanticModel`);

  writeJson(path.join(smDir, '.platform'), {
    $schema: PLATFORM_SCHEMA,
    metadata: { type: 'SemanticModel', displayName: reportName },
    config: {
      version: '2.0',
      logicalId: crypto.randomUUID(),
    },
  });

  writeJson(path.join(smDir, 'definition.pbism'), { version: '1.0' });

  if (sm.source === 'inline') {
    writeJson(path.join(smDir, 'model.bim'), buildModelBim(entity, sm));
  }

  // ── Report ────────────────────────────────────────────────────────────
  const rDir = path.join(outputDir, `${reportName}.Report`);
  const smRelPath = sm.source === 'path' ? sm.modelPath : `../${reportName}.SemanticModel`;

  writeJson(path.join(rDir, '.platform'), {
    $schema: PLATFORM_SCHEMA,
    metadata: { type: 'Report', displayName: reportName },
    config: { version: '2.0', logicalId: crypto.randomUUID() },
  });

  writeJson(path.join(rDir, 'definition.pbir'), {
    version: '4.0',
    datasetReference: { byPath: { path: smRelPath } },
  });

  writeJson(path.join(rDir, 'definition', 'version.json'), { version: '2.0.0' });
  writeJson(path.join(rDir, 'definition', 'report.json'), { $schema: REPORT_SCHEMA, themeCollection: {} });

  // ── Pages ─────────────────────────────────────────────────────────────
  const pageIds = pages.map(() => hex20());

  writeJson(path.join(rDir, 'definition', 'pages', 'pages.json'), {
    $schema: PAGES_SCHEMA,
    pageOrder: pageIds,
    activePageName: pageIds[0],
  });

  pages.forEach((page, i) => {
    const pageId  = pageIds[i];
    const pageDir = path.join(rDir, 'definition', 'pages', pageId);

    writeJson(path.join(pageDir, 'page.json'), {
      $schema: PAGE_SCHEMA,
      name: pageId,
      displayName: page.name,
      displayOption: 'FitToPage',
      height: 720,
      width: 1280,
    });

    mkdirp(path.join(pageDir, 'visuals'));

    (page.visuals || []).forEach(visCfg => {
      const vis    = buildVisual(entity, visCfg);
      const visDir = path.join(pageDir, 'visuals', vis.name);
      writeJson(path.join(visDir, 'visual.json'), vis);
    });
  });

  // ── .pbip manifest ────────────────────────────────────────────────────
  writeJson(path.join(outputDir, `${reportName}.pbip`), {
    version: '1.0',
    artifacts: [{ report: { path: `${reportName}.Report` } }],
  });

  console.log(`Generated: ${path.join(outputDir, reportName + '.pbip')}`);
  console.log(`Pages: ${pages.map((p, i) => `${p.name} (${pageIds[i]})`).join(', ')}`);
  return { outputDir, reportName, pageIds };
}

module.exports = { generate };
