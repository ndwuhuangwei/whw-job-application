#!/usr/bin/env bash
# Usage: bash build.sh [filename.tex] [output.pdf]
set -euo pipefail
src_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
cd -- "$src_dir"
if (( $# > 2 )); then
  printf 'Usage: bash build.sh [filename.tex] [output.pdf]\n' >&2
  exit 2
fi
input="${1:-}"
output="${2:-resume.pdf}"
if [[ -z "$input" ]]; then
  if [[ -f resume.tex ]]; then
    input=resume.tex
  else
    shopt -s nullglob
    candidates=(*.tex)
    if (( ${#candidates[@]} != 1 )); then
      printf 'Specify one .tex file in the src directory.\n' >&2
      exit 2
    fi
    input="${candidates[0]}"
  fi
fi
case "$input" in
  */*|*\\*|-*|.*) printf 'Input must be a .tex basename inside src.\n' >&2; exit 2 ;;
esac
case "$output" in
  */*|*\\*|-*|.*) printf 'Output must be a .pdf basename.\n' >&2; exit 2 ;;
esac
[[ "$input" == *.tex && -f "$input" ]] || { printf 'Missing .tex source.\n' >&2; exit 2; }
[[ "$output" == *.pdf ]] || { printf 'Output must end with .pdf.\n' >&2; exit 2; }
command -v xelatex >/dev/null || { printf 'XeLaTeX is not available on PATH.\n' >&2; exit 127; }
target="$src_dir/../$output"
[[ ! -d "$target" ]] || { printf 'Output path is a directory.\n' >&2; exit 2; }
build_dir="$(mktemp -d "$src_dir/.build.XXXXXX")"
finish() {
  result=$?
  if (( result == 0 )); then
    resolved_build="$(cd -- "$build_dir" && pwd -P)"
    if [[ "$resolved_build" == "$src_dir"/.build.* && ! -L "$build_dir" ]]; then
      rm -rf -- "$resolved_build"
    else
      printf 'Unexpected build directory; retained for inspection.\n' >&2
      exit 1
    fi
  else
    printf 'Build failed; diagnostics retained at: %s\n' "$build_dir" >&2
  fi
}
trap finish EXIT
for pass in 1 2; do
  xelatex -no-shell-escape -interaction=nonstopmode -halt-on-error -file-line-error \
    -jobname=resume -output-directory="$build_dir" "$input" > "$build_dir/pass-$pass.txt" 2>&1 || {
      cat -- "$build_dir/pass-$pass.txt" >&2
      exit 1
    }
done
[[ -s "$build_dir/resume.pdf" ]] || { printf 'No PDF was produced.\n' >&2; exit 1; }
# Only replace the delivered PDF after both real compilations succeed.
mv -f -- "$build_dir/resume.pdf" "$target"
printf 'PDF: %s\n' "$target"
