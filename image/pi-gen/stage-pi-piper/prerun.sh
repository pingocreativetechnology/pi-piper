#!/bin/bash -e
# Skip this stage if a previous export already finished it.
if [ ! -f "${STAGE_WORK_DIR}/SKIP" ]; then
  echo "Pi Piper stage"
fi
