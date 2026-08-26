# Security and private data

## Credentials

Never commit or paste an ENTSO-E security token. Store it locally in the
`ENTSOE_SECURITY_TOKEN` environment variable. The `.env` file is ignored by Git.

If a credential is accidentally committed:

1. revoke or rotate it immediately at the issuing service;
2. remove it from the repository and its Git history;
3. do not rely on deleting only the latest file version.

## Market data

Official HEnEx workbooks and cached ENTSO-E responses are intentionally excluded from the
repository. Contributors are responsible for reviewing source terms before retrieving,
processing or redistributing market data.

## Reporting issues

Do not open a public issue containing credentials, private data or licensed raw data.
Use the repository owner's private contact route instead.
