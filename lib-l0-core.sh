#!/usr/bin/env bash
# Shared L0 helpers and baseline for golden-image bootstrap scripts.

if [[ -n "${LIB_L0_CORE_SOURCED:-}" ]]; then
    return 0
fi
LIB_L0_CORE_SOURCED=1

NC=$'\033[0m'
BOLD=$'\033[1m'
DIM=$'\033[2m'
RED=$'\033[31m'
GREEN=$'\033[32m'
YELLOW=$'\033[33m'
BLUE=$'\033[34m'

DRY_RUN="${DRY_RUN:-0}"
SSH_PORT="${SSH_PORT:-22}"
ADMIN_USER="${ADMIN_USER:-admin}"
NODE_RELEASE="${NODE_RELEASE:-/etc/node-release}"
IMAGE_VERSION="${IMAGE_VERSION:-gold-unknown-v0}"
SSH_HARDENING_FILE="${SSH_HARDENING_FILE:-/etc/ssh/sshd_config.d/50-nodefactory-hardening.conf}"
NODE_LAYOUT_ROOT="${NODE_LAYOUT_ROOT:-/opt/node}"
AGENT_LAYOUT_ROOT="${AGENT_LAYOUT_ROOT:-/opt/agent}"
NODE_STATE_ROOT="${NODE_STATE_ROOT:-/var/lib/node}"
NODE_LOG_ROOT="${NODE_LOG_ROOT:-/var/log/node}"
L0_ALLOW_NON_ROOT="${L0_ALLOW_NON_ROOT:-0}"
NODE_HOSTNAME="${NODE_HOSTNAME:-$(hostname 2>/dev/null || echo unknown-node)}"

header() {
    echo ""
    echo -e "${BOLD}${BLUE}==>${NC} ${BOLD}$*${NC}"
}

success() {
    echo -e "${GREEN}[ok]${NC} $*"
}

warn() {
    echo -e "${YELLOW}[warn]${NC} $*"
}

skip() {
    echo -e "${DIM}[skip]${NC} $*"
}

die() {
    echo -e "${RED}[fatal]${NC} $*" >&2
    exit 1
}

run() {
    if [[ "${DRY_RUN}" -eq 1 ]]; then
        echo -e "${DIM}[dry-run]${NC} $*"
        return 0
    fi
    "$@"
}

write_text_file() {
    local path="$1"
    local content="$2"

    if [[ "${DRY_RUN}" -eq 1 ]]; then
        echo -e "${DIM}[dry-run] write ${path}${NC}"
        return 0
    fi

    mkdir -p "$(dirname "${path}")"
    printf '%s' "${content}" > "${path}"
}

append_text_file() {
    local path="$1"
    local content="$2"

    if [[ "${DRY_RUN}" -eq 1 ]]; then
        echo -e "${DIM}[dry-run] append ${path}${NC}"
        return 0
    fi

    mkdir -p "$(dirname "${path}")"
    printf '%s' "${content}" >> "${path}"
}

usage() {
    cat <<EOF
Usage:
  sudo bash <wrapper>.sh [options]

Options:
  --dry-run                 Print actions without changing the system
  --admin-user <name>       Admin username to create/maintain (default: ${ADMIN_USER})
  --ssh-port <port>         SSH port to allow in UFW (default: ${SSH_PORT})
  --node-release <path>     Override node-release path (default: ${NODE_RELEASE})
  --image-version <value>   Version stamp to write to ${NODE_LAYOUT_ROOT}/VERSION
  --hostname <value>        Override hostname recorded in node-release
  --help                    Show this help

Environment overrides:
  L0_ALLOW_NON_ROOT=1       Allow execution without root for dry-run/testing
EOF
}

parse_l0_args() {
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --dry-run)
                DRY_RUN=1
                shift
                ;;
            --admin-user)
                [[ $# -ge 2 ]] || die "--admin-user requires a value"
                ADMIN_USER="$2"
                shift 2
                ;;
            --ssh-port)
                [[ $# -ge 2 ]] || die "--ssh-port requires a value"
                SSH_PORT="$2"
                shift 2
                ;;
            --node-release)
                [[ $# -ge 2 ]] || die "--node-release requires a value"
                NODE_RELEASE="$2"
                shift 2
                ;;
            --image-version)
                [[ $# -ge 2 ]] || die "--image-version requires a value"
                IMAGE_VERSION="$2"
                shift 2
                ;;
            --hostname)
                [[ $# -ge 2 ]] || die "--hostname requires a value"
                NODE_HOSTNAME="$2"
                shift 2
                ;;
            --help|-h)
                usage
                exit 0
                ;;
            *)
                die "Unknown argument: $1"
                ;;
        esac
    done
}

require_root_if_needed() {
    if [[ "${EUID}" -eq 0 ]]; then
        return 0
    fi

    if [[ "${L0_ALLOW_NON_ROOT}" -eq 1 && "${DRY_RUN}" -eq 1 ]]; then
        warn "Running non-root in dry-run mode for validation"
        return 0
    fi

    die "This script must run as root. Use sudo or set L0_ALLOW_NON_ROOT=1 with --dry-run for validation."
}

show_l0_config() {
    header "L0 CORE CONFIG"
    echo "  ADMIN_USER=${ADMIN_USER}"
    echo "  SSH_PORT=${SSH_PORT}"
    echo "  NODE_RELEASE=${NODE_RELEASE}"
    echo "  IMAGE_VERSION=${IMAGE_VERSION}"
    echo "  NODE_HOSTNAME=${NODE_HOSTNAME}"
    echo "  DRY_RUN=${DRY_RUN}"
}

ensure_group_exists() {
    local group_name="$1"

    if getent group "${group_name}" >/dev/null 2>&1; then
        skip "Group already exists: ${group_name}"
        return 0
    fi

    run groupadd "${group_name}"
    success "Created group: ${group_name}"
}

ensure_admin_user() {
    header "Ensuring admin user"

    ensure_group_exists sshusers

    if id -u "${ADMIN_USER}" >/dev/null 2>&1; then
        skip "User already exists: ${ADMIN_USER}"
    else
        run useradd -m -s /bin/bash -G sudo,sshusers "${ADMIN_USER}"
        run passwd -l "${ADMIN_USER}"
        success "Created locked admin user: ${ADMIN_USER}"
    fi

    if id -u "${ADMIN_USER}" >/dev/null 2>&1; then
        run usermod -aG sudo,sshusers "${ADMIN_USER}"
        success "Ensured ${ADMIN_USER} is in sudo and sshusers"
    fi
}

create_node_layout() {
    header "Creating node layout"

    run mkdir -p \
        "${NODE_LAYOUT_ROOT}/bin" \
        "${NODE_LAYOUT_ROOT}/docs" \
        "${NODE_LAYOUT_ROOT}/templates" \
        "${AGENT_LAYOUT_ROOT}/baseline" \
        "${NODE_STATE_ROOT}" \
        "${NODE_LOG_ROOT}"

    write_text_file "${NODE_LAYOUT_ROOT}/VERSION" "${IMAGE_VERSION}"$'\n'
    success "Node layout ready under ${NODE_LAYOUT_ROOT}"
}

configure_ssh_hardening() {
    header "Configuring SSH hardening"

    local content
    content=$(cat <<EOF
PasswordAuthentication no
KbdInteractiveAuthentication no
PermitRootLogin no
PubkeyAuthentication yes
MaxAuthTries 3
AllowGroups sshusers
X11Forwarding no
AllowAgentForwarding no
EOF
)

    if [[ ! -d "$(dirname "${SSH_HARDENING_FILE}")" ]]; then
        warn "SSH drop-in directory missing: $(dirname "${SSH_HARDENING_FILE}")"
        return 0
    fi

    write_text_file "${SSH_HARDENING_FILE}" "${content}"

    if command -v systemctl >/dev/null 2>&1; then
        run systemctl restart ssh || run systemctl restart sshd
    else
        warn "systemctl unavailable; SSH service restart skipped"
    fi

    success "SSH hardening drop-in ready at ${SSH_HARDENING_FILE}"
}

configure_ufw_baseline() {
    header "Configuring UFW baseline"

    if ! command -v ufw >/dev/null 2>&1; then
        warn "ufw not installed; skipping firewall baseline"
        return 0
    fi

    run ufw default deny incoming
    run ufw default allow outgoing
    run ufw allow "${SSH_PORT}/tcp"
    run ufw --force enable

    success "UFW baseline configured for SSH port ${SSH_PORT}"
}

write_node_release_stub() {
    header "Initializing node-release"

    local now_utc
    now_utc="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

    local content
    content=$(cat <<EOF
IMAGE_VERSION=${IMAGE_VERSION}
ADMIN_USER=${ADMIN_USER}
NODE_HOSTNAME=${NODE_HOSTNAME}
SSH_PORT=${SSH_PORT}
L0_DATE=${now_utc}
EOF
)

    write_text_file "${NODE_RELEASE}" "${content}"
    success "node-release initialized at ${NODE_RELEASE}"
}

validate_l0_core() {
    header "Validating L0 core"

    local issues=0

    if [[ "${DRY_RUN}" -eq 0 && ! -f "${NODE_LAYOUT_ROOT}/VERSION" ]]; then
        warn "Missing version stamp: ${NODE_LAYOUT_ROOT}/VERSION"
        issues=$((issues + 1))
    fi

    if [[ "${DRY_RUN}" -eq 0 && ! -f "${NODE_RELEASE}" ]]; then
        warn "Missing node-release file: ${NODE_RELEASE}"
        issues=$((issues + 1))
    fi

    if ! command -v sshd >/dev/null 2>&1; then
        warn "sshd not found; SSH hardening may not apply on this system"
        issues=$((issues + 1))
    fi

    if [[ "${issues}" -eq 0 ]]; then
        success "L0 core validation clean"
    else
        warn "L0 core validation found ${issues} issue(s)"
    fi
}

l0_core_main() {
    parse_l0_args "$@"
    require_root_if_needed
    show_l0_config

    header "L0 CORE"
    ensure_admin_user
    create_node_layout
    configure_ssh_hardening
    configure_ufw_baseline
    write_node_release_stub
    validate_l0_core
    success "L0 core baseline ready."
}
