#!/bin/sh
set -e

thisdir="$(dirname "$0")"
ctx="$1"
shift

ver="$(basename "$ctx")"
image_hash_file="$thisdir/image.$ver.hsh"

if [ -n "$FORCE_IMAGE" -o ! -f "$image_hash_file" ]; then
    docker build --iidfile "$image_hash_file" "$ctx"
fi

image=$(cat "$image_hash_file")

mkdir -p .pytest_cache_$ver

docker run -it --rm \
  -v $PWD:/work:ro \
  -v "$(realpath .pytest_cache_$ver)":/cache \
  -w /work \
  $image py.test -o cache_dir=/cache "$@"
