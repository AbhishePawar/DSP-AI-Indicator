/** EPIC-F000 — Frontend foundation public exports. */

export {
  API_CONTRACT_TARGET,
  BACKEND_PLATFORM_TARGET,
  FRONTEND_FOUNDATION_EPIC,
  FRONTEND_FOUNDATION_STATUS,
  FRONTEND_FOUNDATION_VERSION,
} from "./version";
export { technologyDecisions } from "./technology";
export {
  breakpointTokens,
  colorTokens,
  forbiddenAccents,
  radiusTokens,
  spacingTokens,
  typographyTokens,
  zIndexTokens,
} from "./tokens/design-tokens";
export { FROZEN_FEATURE_ROUTES, ROUTE_GROUPS } from "./routes/freeze";
export {
  footerSpec,
  globalLayoutSpec,
  headerSpec,
  sidebarSpec,
} from "./layout/spec";
export {
  stateArchitecture,
  uiStoreDefaults,
  type UiStoreState,
} from "./state/architecture";
export { apiStrategy, resolveListState, type ApiUxState } from "./api/strategy";
export {
  emptyStrategy,
  errorStrategy,
  loadingStrategy,
  notificationStrategy,
} from "./ux/strategies";
export { authFlowSpec } from "./auth/flow";
export { componentHierarchy } from "./components/hierarchy";
