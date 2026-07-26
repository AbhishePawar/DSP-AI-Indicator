# Intelligence Workspace — Frontend Guide (EPIC-003)

## Architecture

`
Browser (apps/web)
   │  fetch only
   ▼
/api/v1  (api_platform)
   │
   ▼
dsp_platform.compose_intelligence
`

Forbidden: imports of dsp_platform, FEATURE packages, or any Python domain module.

## Component Guide

| Component | Role |
|---|---|
| AnalysisForm | Ticker / exchange / valuation + statements JSON |
| ValidationBanner | Validation / API errors + retry + correlation ID |
| PipelineTimeline | Stage statuses from stage_summaries |
| BusinessQualityCard | Aggregator summary fields |
| RecommendationCard | Recommendation + MoS + confidence |
| CommitteeConsensusCard | Committee decision + minority notes |
| EvidencePanel | Evidence counts + confidence summary |
| MetricsPanel | Strengths / weaknesses / risks from stage statuses |
| ExecutionMetadataPanel | Timing, versions, limitations |
| HealthIndicator | /health ready state |
| VersionCard | /version |
| CapabilitiesPanel | /capabilities |

## API Integration

Base URL: NEXT_PUBLIC_API_BASE_URL (default http://127.0.0.1:8000/api/v1).

Flow: Validate → Analyse → Display PipelineResult summaries.

## Developer Guide

`ash
cd apps/web
npm install
npm run dev
# open /intelligence
npm test
`

## User Guide

1. Sign in to the web app.
2. Open **Intelligence Workspace** in the sidebar.
3. Load sample or paste financial statement JSON.
4. Click **Validate**, then **Run analyse**.
5. Inspect recommendation, committee, pipeline, evidence, and metadata panels.

## Screenshots

Capture locally after 
pm run dev against a running API (TD-E005 for CI visual pack).
