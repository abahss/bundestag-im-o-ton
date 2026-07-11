#!/bin/bash
set -e

# Format and mount the persistent disk (first boot only)
if ! mountpoint -q /mnt/chromadb; then
  echo "Setting up persistent disk..."

  # Check if disk is already formatted
  if ! blkid ${disk_device}; then
    mkfs.ext4 -m 0 -F -E lazy_itable_init=0,lazy_journal_init=0,discard ${disk_device}
  fi

  mkdir -p /mnt/chromadb
  mount -o discard,defaults ${disk_device} /mnt/chromadb
  chmod a+w /mnt/chromadb

  # Add to fstab for automatic mounting
  echo "UUID=$(blkid -s UUID -o value ${disk_device}) /mnt/chromadb ext4 discard,defaults 0 2" >> /etc/fstab
fi

# Fetch vector data
gsutil -m cp -r 'gs://batch-2170-political-reality-check/data/chroma_store/*' /mnt/chromadb/

# Install Docker
if ! command -v docker &> /dev/null; then
  echo "Installing Docker..."
  apt-get update
  apt-get install -y docker.io
  systemctl enable docker
  systemctl start docker
fi

# Pull and run ChromaDB
echo "Starting ChromaDB..."
docker pull chromadb/chroma:latest

# Stop existing container if running
docker stop chromadb 2>/dev/null || true
docker rm chromadb 2>/dev/null || true

# Run ChromaDB with persistent storage
docker run -d \
  --name chromadb \
  --restart unless-stopped \
  -p 8000:8000 \
  -v /mnt/chromadb:/data \
  -e IS_PERSISTENT=TRUE \
  -e ANONYMIZED_TELEMETRY=FALSE \
  chromadb/chroma:latest
  # -e CHROMA_SERVER_AUTH_CREDENTIALS="your-token" \
  # -e CHROMA_SERVER_AUTH_PROVIDER="chromadb.auth.token_authn.TokenAuthenticationServerProvider" \

echo "ChromaDB startup complete!"
