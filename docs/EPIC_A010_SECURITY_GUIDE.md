# EPIC-A010 — Security Guide

## Trust boundaries

- Identity mutations (create user / assign roles) delegate to A009 — passwords remain hashed
- Admin list responses never include password hashes
- Configuration viewer redacts keys containing SECRET/PASSWORD/TOKEN/KEY/CREDENTIAL
- Audit export is metadata-only

## Compliance

Supports CV-001 / CV-002 / CV-003 operational visibility without weakening
research immutability (RS-001…RS-010).

## Hard prohibitions

- No engine execution from admin routes
- No provider calls
- No research/report/archive mutation
- No scoring / valuation / recommendation generation
