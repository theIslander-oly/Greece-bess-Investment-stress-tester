#!/usr/bin/env bash
# Record or verify the custody of one downloaded official artifact.
#
# Usage: custody_step.sh <artifact-name> <source-run-id> <source-workflow> [published-digest]
#
# When docs/custody/<artifact-name>.json exists, the downloaded copy is verified against
# it and a difference marks the job for failure. When it does not, a record is generated
# for review. Neither path prints an official price: the CLI writes digests and counts.

set -euo pipefail

artifact_name="$1"
source_run_id="$2"
source_workflow="$3"
published_digest="${4:-}"

directory="artifacts/${artifact_name}"
committed="docs/custody/${artifact_name}.json"
mkdir -p custody

if [[ ! -d "$directory" ]]; then
  echo "The ${artifact_name} artifact was not downloaded."
  exit 1
fi

if [[ -f "$committed" ]]; then
  echo "Verifying ${artifact_name} against its committed custody record."
  set +e
  greek-bess verify-custody "$directory" \
    --record "$committed" \
    --report "custody/${artifact_name}.verification.json"
  status=$?
  set -e
  case "$status" in
    0)
      echo "${artifact_name}: verified against the committed custody record." \
        >> "$GITHUB_STEP_SUMMARY"
      ;;
    2)
      echo "${artifact_name}: DID NOT VERIFY against the committed custody record." \
        >> "$GITHUB_STEP_SUMMARY"
      touch custody/verification_failed
      ;;
    *)
      exit "$status"
      ;;
  esac
else
  echo "No committed custody record for ${artifact_name}; recording one."
  digest_args=()
  if [[ -n "$published_digest" ]]; then
    digest_args=(--published-digest "$published_digest")
  fi
  greek-bess record-custody "$directory" \
    --artifact-name "$artifact_name" \
    --source-run-id "$source_run_id" \
    --source-workflow "$source_workflow" \
    "${digest_args[@]}" \
    --output "custody/${artifact_name}.json"
  echo "${artifact_name}: custody record generated from run ${source_run_id}." \
    >> "$GITHUB_STEP_SUMMARY"
fi
