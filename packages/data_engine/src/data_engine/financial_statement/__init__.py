"""Authenticated financial statement subsystem (EPIC-D002)."""

from __future__ import annotations

from data_engine.financial_statement.adapters import (
    ConfiguredHttpStatementAdapter,
    InMemoryAuthenticatedStatementAdapter,
    NullAuthenticatedStatementAdapter,
    build_default_statement_adapter_from_env,
    build_period_from_mapping,
    build_statements_from_mapping,
    normalize_reporting_currency,
)
from data_engine.financial_statement.models import (
    AuthenticatedFinancialStatements,
    AuthenticatedStatementPeriod,
    CompanyIdentity,
    FinancialStatementProvenance,
    StatementField,
    utc_now,
)
from data_engine.financial_statement.registry import FinancialStatementProviderRegistry
from data_engine.financial_statement.service import (
    FinancialStatementPort,
    FinancialStatementService,
    FinancialStatementServiceMetrics,
    StatementProviderHealth,
    StatementQuery,
)
from data_engine.financial_statement.validation import validate_authenticated_statements

__all__ = [
    "AuthenticatedFinancialStatements",
    "AuthenticatedStatementPeriod",
    "CompanyIdentity",
    "ConfiguredHttpStatementAdapter",
    "FinancialStatementPort",
    "FinancialStatementProvenance",
    "FinancialStatementProviderRegistry",
    "FinancialStatementService",
    "FinancialStatementServiceMetrics",
    "InMemoryAuthenticatedStatementAdapter",
    "NullAuthenticatedStatementAdapter",
    "StatementField",
    "StatementProviderHealth",
    "StatementQuery",
    "build_default_statement_adapter_from_env",
    "build_period_from_mapping",
    "build_statements_from_mapping",
    "normalize_reporting_currency",
    "utc_now",
    "validate_authenticated_statements",
]
