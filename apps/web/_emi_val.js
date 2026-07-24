const {
  moatEngine,
  EMI_VERSION,
  ProductionReady,
  FeatureComplete,
  EMI_RELEASE,
  MOAT_CATEGORY_WEIGHTS,
  runEmiProductionValidation,
  benchmarkEmiPipeline,
} = require('./src/lib/moat');

const report = runEmiProductionValidation();
const failed = report.checks.filter(c => !c.ok);
const perf = report.performance;
const complete = moatEngine.demoComplete();
console.log(JSON.stringify({
  EMI_VERSION,
  ProductionReady,
  FeatureComplete,
  stamp: EMI_RELEASE.stamp,
  engine: {
    emiVersion: moatEngine.info.emiVersion,
    productionReady: moatEngine.info.productionReady,
    featureComplete: moatEngine.info.featureComplete,
    overallEnabled: moatEngine.info.overallMoatScoreEnabled,
  },
  weightSum: Object.values(MOAT_CATEGORY_WEIGHTS).reduce((a,b)=>a+b,0),
  reportOk: report.ok,
  failedChecks: failed,
  checkCount: report.checks.length,
  overallScore: complete.analysis.assessment.overallMoatScore,
  perf: {
    categoryDemoMs: perf.categoryDemoMs,
    scoredCategoriesMs: perf.scoredCategoriesMs,
    aggregationMs: perf.aggregationMs,
    dashboardMs: perf.dashboardMs,
    selectorMs: perf.selectorMs,
    deterministic: perf.deterministic,
    serializedBytes: perf.serializedBytes,
  },
}, null, 2));
