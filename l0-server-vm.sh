#!/usr/bin/env bash
# ==============================================================================
# l0-server-vm.sh
# L0 wrapper: Server VM golden image.
#
# Layers on lib-l0-core.sh to produce a VM-ready server baseline.
#
# What this adds to core:
#   - Universal bloat stripping (packages useless on any node, metal or VM)
#   - GRUB serial console (virsh console always works, even if networking dies)
#   - Keeps cloud-init (Phase 2 provisioning engine for VMs)
#   - Stamps node-release with TARGET=vm
#
# What this does NOT add (L2 concerns):
#   - qemu-guest-agent / spice-vdagent (hypervisor-specific, added per node type)
#   - Docker, Tailscale, Node.js, agent user, desktop stack
#   - Swap configuration (node-class-dependent)
#
# Usage:
#   sudo bash l0-server-vm.sh [--dry-run] [--ssh-port <port>] [--admin-user <n>]
#
# Golden build:
#   Server VM = lib-l0-core + l0-server-vm
# ==============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Source the core library
if [[ ! -f "${SCRIPT_DIR}/lib-l0-core.sh" ]]; then
    echo "FATAL: lib-l0-core.sh not found in ${SCRIPT_DIR}" >&2
    exit 1
fi
source "${SCRIPT_DIR}/lib-l0-core.sh"

# ------------------------------------------------------------------------------
# VM defaults (override core defaults before l0_core_main parses flags)
# ------------------------------------------------------------------------------
SSH_PORT="${SSH_PORT:-22}"          # VMs sit behind NAT; port 22 is fine

# ------------------------------------------------------------------------------
# Universal bloat stripping
# Packages that are equally useless on metal and VM. Zero controversy.
# Called by both server-vm and server-metal wrappers.
# Heavier opinionated stripping (snap, BT, CUPS, Avahi, Plymouth, pro-client)
# lives in l0-strip-lean.sh / l0-strip-barebones.sh — separate decision.
# ------------------------------------------------------------------------------
strip_universal_bloat() {
    header "Stripping universal bloat"

    local -a targets=()
    local -a removed=()

    # multipathd — SAN/multipath storage. No homelab node uses this.
    if dpkg -l multipathd 2>/dev/null | grep -q '^ii'; then
        targets+=(multipath-tools)
    fi

    # ModemManager — cellular modem management. Never.
    if dpkg -l modemmanager 2>/dev/null | grep -q '^ii'; then
        targets+=(modemmanager)
    fi

    # apport — crash reporter / telemetry uploader
    if dpkg -l apport 2>/dev/null | grep -q '^ii'; then
        targets+=(apport)
    fi

    # whoopsie — Ubuntu error tracker
    if dpkg -l whoopsie 2>/dev/null | grep -q '^ii'; then
        targets+=(whoopsie)
    fi

    # popularity-contest — package usage telemetry
    if dpkg -l popularity-contest 2>/dev/null | grep -q '^ii'; then
        targets+=(popularity-contest)
    fi

    if [[ ${#targets[@]} -eq 0 ]]; then
        skip "No universal bloat packages found"
        return 0
    fi

    for pkg in "${targets[@]}"; do
        run apt-get purge -y "$pkg" && removed+=("$pkg")
    done
    run apt-get autoremove -y

    success "Stripped ${#removed[@]} bloat package(s): ${removed[*]:-none}"
}

# ------------------------------------------------------------------------------
# GRUB serial console
# Ensures `virsh console <vm>` works even when networking is dead.
# Non-destructive: appends console= to existing GRUB_CMDLINE, keeps graphical
# boot intact for desktop augmentation later.
# ------------------------------------------------------------------------------
configure_grub_serial_console() {
    header "Configuring GRUB serial console for VM"

    local grub_file="/etc/default/grub"

    if [[ ! -f "${grub_file}" ]]; then
        warn "No ${grub_file} found; skipping serial console setup"
        return 0
    fi

    # Only add if not already configured
    if grep -q 'console=ttyS0' "${grub_file}"; then
        skip "Serial console already configured in GRUB"
        return 0
    fi

    if [[ "${DRY_RUN}" -eq 1 ]]; then
        echo -e "${DIM}[dry-run] append console=ttyS0,115200 to GRUB_CMDLINE_LINUX${NC}"
        return 0
    fi

    # Append serial console to existing GRUB_CMDLINE_LINUX
    if grep -q '^GRUB_CMDLINE_LINUX="' "${grub_file}"; then
        sed -i 's/^GRUB_CMDLINE_LINUX="\(.*\)"/GRUB_CMDLINE_LINUX="\1 console=tty0 console=ttyS0,115200"/' "${grub_file}"
    else
        echo 'GRUB_CMDLINE_LINUX="console=tty0 console=ttyS0,115200"' >> "${grub_file}"
    fi

    # Enable serial terminal output in GRUB menu itself
    if ! grep -q '^GRUB_TERMINAL=' "${grub_file}"; then
        echo 'GRUB_TERMINAL="console serial"' >> "${grub_file}"
        echo 'GRUB_SERIAL_COMMAND="serial --speed=115200"' >> "${grub_file}"
    fi

    run update-grub

    success "GRUB serial console enabled (ttyS0@115200)"
}

# ------------------------------------------------------------------------------
# Stamp node-release with VM target info
# Appends to the stub already written by lib-l0-core.sh
# ------------------------------------------------------------------------------
stamp_vm_target() {
    header "Stamping node-release with VM target"

    if [[ "${DRY_RUN}" -eq 1 ]]; then
        echo -e "${DIM}[dry-run] append TARGET=vm to ${NODE_RELEASE}${NC}"
        return 0
    fi

    cat >> "${NODE_RELEASE}" <<EOF
TARGET=vm
L0_WRAPPER=l0-server-vm
CLOUD_INIT=preserved
GUEST_AGENT=deferred-to-L2
EOF

    success "node-release stamped: TARGET=vm"
}

# ------------------------------------------------------------------------------
# Validate VM-specific expectations
# ------------------------------------------------------------------------------
validate_vm_layer() {
    header "Validating VM layer"

    local violations=0

    # cloud-init should still be present on VM images
    if ! command -v cloud-init >/dev/null 2>&1; then
        warn "cloud-init not found — expected on VM images for Phase 2 provisioning"
        violations=$((violations + 1))
    fi

    # Universal bloat should be gone
    for pkg in multipath-tools modemmanager apport whoopsie popularity-contest; do
        if dpkg -l "$pkg" 2>/dev/null | grep -q '^ii'; then
            warn "Bloat package still installed: ${pkg}"
            violations=$((violations + 1))
        fi
    done

    if [[ "${violations}" -eq 0 ]]; then
        success "VM layer validation clean"
    else
        warn "VM layer validation found ${violations} issue(s)"
    fi
}

# ------------------------------------------------------------------------------
# Main
# ------------------------------------------------------------------------------
l0_server_vm_main() {
    # Run the full L0 core first
    l0_core_main "$@"

    header "L0 SERVER-VM LAYER"

    strip_universal_bloat
    configure_grub_serial_console
    stamp_vm_target
    validate_vm_layer

    header "L0 SERVER-VM COMPLETE"
    success "Server VM golden baseline ready."
    echo ""
    echo "  Next steps:"
    echo "    1. Set ${ADMIN_USER} password:  sudo passwd ${ADMIN_USER}"
    echo "    2. Inject SSH pubkey:           ssh-copy-id or manual"
    echo "    3. Seal:                        run generalize, power off, template"
    echo "    4. Desktop?                     stack l0-augment-desktop.sh on top"
    echo ""
}

l0_server_vm_main "$@"
