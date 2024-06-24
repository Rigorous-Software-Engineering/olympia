#!/bin/bash
set -xe

DOCKERDIR=$(readlink -f $(dirname "$0")/..)/dockers

# Build echidna image
echo "[*] Build maze-echidna Docker image..."
cd $DOCKERDIR/echidna
docker build -t maze-echidna .
echo "[*] Done!"

# Build echidna image
echo "[*] Build maze-ityfuzz Docker image..."
cd $DOCKERDIR/ityfuzz
docker build -t maze-ityfuzz .
echo "[*] Done!"

# Build foundry image
echo "[*] Build maze-foundry Docker image..."
cd $DOCKERDIR/foundry
docker build -t maze-foundry .
echo "[*] Done!"

# Build medusa image
echo "[*] Build maze-medusa Docker image..."
cd $DOCKERDIR/medusa
docker build -t maze-medusa .
echo "[*] Done!"
