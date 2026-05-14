  #!/usr/bin/env sh
  set -eu

  INTERVAL="${INTERVAL:-5m}"
  SYMBOLS="${SYMBOLS:-SENSEX}"              # e.g. "NIFTY SENSEX"
  COMPOSE="${COMPOSE:-sudo docker compose}" # override if you don't use sudo
  CHUNK_DAYS="${CHUNK_DAYS:-27}"            # safe for 5m; adjust if needed

  END_DATE="${END_DATE:-$(date +%F)}"
  START_DATE="${START_DATE:-$(date -d "${END_DATE} - 365 days" +%F)}"

  end_s="$(date -d "${END_DATE}" +%s)"

  echo "Backfill range: ${START_DATE} -> ${END_DATE} (interval=${INTERVAL}, chunk_days=${CHUNK_DAYS})"
  echo "Symbols: ${SYMBOLS}"
  echo

  current="${START_DATE}"
  while [ "$(date -d "${current}" +%s)" -le "${end_s}" ]; do
    chunk_end="$(date -d "${current} + ${CHUNK_DAYS} days" +%F)"
    chunk_end_s="$(date -d "${chunk_end}" +%s)"
    if [ "${chunk_end_s}" -gt "${end_s}" ]; then
      chunk_end="${END_DATE}"
    fi

    for sym in ${SYMBOLS}; do
      echo "==> ${sym}: ${current} -> ${chunk_end}"
      ${COMPOSE} exec backend python -m backend.ingestion.cli backfill \
        --source upstox --symbol "${sym}" --start "${current}" --end "${chunk_end}" --interval "${INTERVAL}"
      echo
    done

    # move to next day after chunk_end
    current="$(date -d "${chunk_end} + 1 day" +%F)"
  done

  echo "Done."