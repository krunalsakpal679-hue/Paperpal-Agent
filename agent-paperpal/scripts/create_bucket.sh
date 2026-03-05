#!/bin/bash
# scripts/create_bucket.sh
# Create the default S3 bucket in MinIO for local development

set -euo pipefail

MINIO_ENDPOINT="${AWS_S3_ENDPOINT_URL:-http://localhost:9000}"
MINIO_USER="${MINIO_ROOT_USER:-minioadmin}"
MINIO_PASS="${MINIO_ROOT_PASSWORD:-minioadmin}"
BUCKET="${AWS_S3_BUCKET:-paperpal-uploads}"

echo "🪣 Creating bucket '${BUCKET}' in MinIO at ${MINIO_ENDPOINT}..."

# Configure mc alias
mc alias set local "${MINIO_ENDPOINT}" "${MINIO_USER}" "${MINIO_PASS}"

# Create bucket (ignore if exists)
mc mb --ignore-existing "local/${BUCKET}"

# Set download policy
mc anonymous set download "local/${BUCKET}"

echo "✅ Bucket '${BUCKET}' is ready!"
