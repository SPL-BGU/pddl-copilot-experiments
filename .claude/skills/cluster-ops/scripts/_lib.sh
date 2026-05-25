# Shared boilerplate for the cluster-ops scripts.
# Source from each script:
#   source "$(dirname "${BASH_SOURCE[0]}")/_lib.sh"

set -eo pipefail

# Remote SSH target — env-overridable per invocation.
: "${REMOTE_USER:=omereliy}"
: "${REMOTE_HOST:=slurm.bgu.ac.il}"

# Extract a block of leading-`#`-comments from the caller's source and print
# it as a help blurb. Usage: `_show_help <start_line> <end_line>`. Strips the
# leading "# " (or "#") prefix from each line.
_show_help() {
    sed -n "${1},${2}p" "${BASH_SOURCE[1]}" | sed 's/^# \{0,1\}//'
}
