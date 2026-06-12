# Security & responsible use

JANUS is decision **support**. By construction it has no execution capability — it
emits a recommendation for a human to approve or override, and never acts on the
world. "Never auto-executes" is a structural property, not a configuration flag.
Treat its output as advisory; a human is accountable for every decision.

## Data & secrets

The decision corpus is entirely synthetic (a fictional logistics company). No real
organizational data, PII, or credentials are committed. Azure credentials are
resolved at runtime via `DefaultAzureCredential` / managed identity — there are no
keys in this repository or in `.env`.

## Reporting a vulnerability

This is a hackathon submission, not a production deployment. If you find a security
issue in the code, please open a private report via GitHub Security Advisories on
this repository rather than a public issue.

## Scope & limitations

JANUS abstains rather than guesses when precedent is thin or a lesson can't be
grounded. It is not a substitute for legal, compliance, or financial review. The
simulation is a transparent, seeded cost model — directionally useful for contrast,
not a forecast of real-world outcomes.
