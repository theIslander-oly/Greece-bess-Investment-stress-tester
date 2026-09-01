#!/usr/bin/env bash
# Record or verify the custody of one downloaded official artifact.
#
# Usage: custody_step.sh <artifact-name> <source-run-id> <source-workflow> \
#          [published-digest] [mode]
#
# mode "auto" (the default) verifies against docs/custody/<artifact-name>.json when that
# record exists and records one when it does not. mode "record" always records, which is
# how a re-record against a replacement artifact is produced without first deleting the
# committed record: deleting it to make recording happen is indistinguishable from
# tampering with the evidence, and the procedure forbids it.
#
# Neither mode ever writes to docs/custody/. A generated record is written to custody/ and
# uploaded for review, so replacing a committed record stays a reviewed commit and a
# decision entry, never a side effect of a job. Neither path prints an official price: the
# CLI writes digests and counts.

set -euo pipefail

artifact_name="$1"
source_run_id="$2"
source_workflow="$3"
published_digest="${4:-}"
mode="${5:-auto}"

case "$mode" in
  auto|record) ;;
  *)
    echo "Unknown custody mode: ${mode} (expected 'auto' or 'record')."
    exit 1
    ;;
esac

directory="artifacts/${artifact_name}"
committed="docs/custody/${artifact_name}.json"
mkdir -p custody

if [[ ! -d "$directory" ]]; then
  echo "The ${artifact_name} artifact was not downloaded."
  exit 1
fi

if [[ -f "$committed" && "$mode" == "auto" ]]; then
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
  if [[ -f "$committed" ]]; then
    echo "Re-recording ${artifact_name} from run ${source_run_id} at explicit request."
    echo "The committed record is left untouched; review the uploaded record before"
    echo "replacing it, and record the replacement as a decision."
  else
    echo "No committed custody record for ${artifact_name}; recording one."
  fi
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
  echo "${artifact_name}: custody record generated from run ${source_run_id} (mode ${mode})." \
    >> "$GITHUB_STEP_SUMMARY"
fi
