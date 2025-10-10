#!/bin/sh
set -e

thisdir="$(dirname "$0")"
ctx="$1"
shift

ver="$(basename "$ctx")"

if [ -z "$BUILD_IMAGE" ]; then
    docker build --iidfile "$thisdir/image.hsh" "$ctx"
fi
image=$(cat "$thisdir/image.hsh")

mkdir -p .pytest_cache_$ver

docker run -it --rm \
  -v $PWD:/work:ro \
  -v "$(realpath .pytest_cache_$ver)":/cache \
  -w /work \
  $image py.test -o cache_dir=/cache "$@"
