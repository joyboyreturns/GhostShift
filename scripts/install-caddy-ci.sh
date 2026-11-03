#!/bin/sh
set -eu
# Linux CI only. Native macOS verification uses the installed Homebrew Caddy binary.
[ "$(uname -s)" = Linux ] || { echo 'This installer supports Linux CI only.' >&2; exit 1; }
case "$(uname -m)" in
  x86_64) caddy_arch=amd64 ;;
  aarch64|arm64) caddy_arch=arm64 ;;
  *) echo 'Unsupported Caddy architecture.' >&2; exit 1 ;;
esac
caddy_version=2.11.7
caddy_destination=${1:?Pass the CI binary directory}
caddy_temporary=$(mktemp -d)
trap 'rm -rf "$caddy_temporary"' EXIT HUP INT TERM
caddy_archive="caddy_${caddy_version}_linux_${caddy_arch}.tar.gz"
caddy_release="https://github.com/caddyserver/caddy/releases/download/v${caddy_version}"
curl --fail --silent --show-error --location --retry 3 --max-time 60 "$caddy_release/$caddy_archive" --output "$caddy_temporary/$caddy_archive"
curl --fail --silent --show-error --location --retry 3 --max-time 60 "$caddy_release/caddy_${caddy_version}_checksums.txt" --output "$caddy_temporary/checksums.txt"
python3 - "$caddy_temporary" "$caddy_archive" <<'PY'
import hashlib
import sys
from pathlib import Path
folder, filename = Path(sys.argv[1]), sys.argv[2]
checksums = dict((line.split()[1].lstrip('*'), line.split()[0])
                 for line in (folder / 'checksums.txt').read_text().splitlines() if line.strip())
if hashlib.sha256((folder / filename).read_bytes()).hexdigest() != checksums.get(filename):
    raise SystemExit('Caddy archive checksum verification failed')
PY
mkdir -p "$caddy_destination"
tar -xzf "$caddy_temporary/$caddy_archive" -C "$caddy_temporary" caddy
install -m 755 "$caddy_temporary/caddy" "$caddy_destination/caddy"
"$caddy_destination/caddy" version
