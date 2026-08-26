# Secure ENTSO-E Retrieval with GitHub Actions

This manual workflow is for users who cannot run the project locally. The personal
ENTSO-E token is stored as an encrypted GitHub repository secret and is never committed
to the repository, included in an artifact or printed by the project.

## One-time setup

1. Open the GitHub repository.
2. Select **Settings**.
3. Select **Secrets and variables** and then **Actions**.
4. Select **New repository secret**.
5. Enter the name `ENTSOE_SECURITY_TOKEN` exactly.
6. Paste a current private ENTSO-E token into the secret value.
7. Select **Add secret**.

Do not use a token that has appeared in chat, source code, an issue, a commit, a workflow
input or a screenshot. Generate a replacement first. GitHub does not reveal a repository
secret after it is saved.

## Run the official-data fetch

1. Open the repository's **Actions** tab.
2. Select **Fetch official ENTSO-E prices**.
3. Select **Run workflow**.
4. Leave the default boundaries to retrieve the HEnEx acceptance days:
   - start: `2026-08-23T22:00Z`
   - end: `2026-08-25T22:00Z`
5. Select the green **Run workflow** button.
6. Wait for the run to finish successfully.

The workflow installs the project, retrieves Greek A44 Day-Ahead Market prices, performs
the normal complete-day quality checks and retains only the normalized CSV and quality
JSON as a seven-day GitHub artifact. Raw XML remains on the temporary runner and is not
uploaded.

## Retrieve the result

Open the completed workflow run and download the
`entsoe-greek-dam-acceptance` artifact, or allow an authorized project assistant to read
the completed run through the connected GitHub integration.

After successful acceptance, the repository secret can be deleted from
**Settings → Secrets and variables → Actions**. Revoking or regenerating the corresponding
token at ENTSO-E provides the additional assurance that it can no longer be used.

