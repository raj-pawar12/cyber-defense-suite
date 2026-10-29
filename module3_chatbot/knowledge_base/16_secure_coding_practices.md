# Secure coding practices

## Habits that prevent most problems
Validate all input on the server and treat every input as untrusted. Use parameterised queries. Keep secrets such as API keys and passwords out of source code. Store them in environment variables or a secrets manager and never commit a .env file to GitHub. Update dependencies and watch for security advisories. Give each component the least privilege it needs.

## Authentication and sessions
Hash passwords with a slow algorithm. Add rate limiting and lockouts against guessing. Use secure, HttpOnly cookies and expire sessions.

## Process
Review code, run automated tests and static analysis, log security events without logging secrets, and show users generic error messages instead of stack traces. If a secret is ever committed by mistake, treat it as leaked and rotate it, because deleting the file does not remove it from history.
