#!/bin/bash
set -e
if [ -n "$DEMO_EXPIRES_DATE" ]; then
    TODAY=$(date +%Y-%m-%d)
    if [[ "$TODAY" > "$DEMO_EXPIRES_DATE" ]]; then
        echo "============================================"
        echo " DEMO EXPIRED on $DEMO_EXPIRES_DATE"
        echo " Please contact your vendor to renew access."
        echo "============================================"
        exit 0
    fi
fi
exec "$@"
