#!/bin/sh
set -e

mc alias set local http://minio:9000 "${MINIO_ACCESS_KEY}" "${MINIO_SECRET_KEY}"

if ! mc ls local/"${MINIO_BUCKET_DOCUMENTS}" > /dev/null 2>&1; then
  mc mb local/"${MINIO_BUCKET_DOCUMENTS}"
  echo "Bucket '${MINIO_BUCKET_DOCUMENTS}' creado."
else
  echo "Bucket '${MINIO_BUCKET_DOCUMENTS}' ya existe."
fi
