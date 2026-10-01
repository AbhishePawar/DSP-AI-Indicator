# Preview-only credentials

Existing DSP development seed account (not production).
- Email: `admin@dspai.local`
- Username: `admin`
- Password: `PwlY2YzCSZw003K9FORpK-sFwGocfA!8aA`
- Origin: https://32e351be-0143-4341-9d1b-cfbd1e47afd6.preview.emergentagent.com
- Auth: UI uses `/api/v1/auth/enterprise/login` with `{identifier,password}`; RBAC `/api/v1/auth/rbac/login` uses `{username,password}`. Cookie session + CSRF required for authenticated mutations. Legacy `/api/v1/auth/login` is intentionally unavailable and is no longer a frontend fallback.
- External OAuth, SMS, investment-provider keys are not configured.
