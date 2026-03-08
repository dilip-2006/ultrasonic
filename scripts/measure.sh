#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────────────────
#  📏  Ultrasonic — On-Demand Measurement Client
#      Professional Terminal Launcher
# ──────────────────────────────────────────────────────────────────────────────

set -euo pipefail

# ── Colour palette ─────────────────────────────────────────────────────────────
C_RESET='\033[0m'
C_BOLD='\033[1m'
C_DIM='\033[2m'
C_CYAN='\033[96m'
C_GREEN='\033[92m'
C_YELLOW='\033[93m'
C_RED='\033[91m'
C_MAGENTA='\033[95m'
C_WHITE='\033[97m'

# ── Helpers ────────────────────────────────────────────────────────────────────
print_line() { printf "${C_DIM}${C_CYAN}%s${C_RESET}\n" "$(printf '─%.0s' {1..56})"; }
print_dline(){ printf "${C_CYAN}${C_BOLD}%s${C_RESET}\n" "$(printf '═%.0s' {1..56})"; }

ok()   { printf "  ${C_GREEN}${C_BOLD}✔${C_RESET}  $*\n"; }
warn() { printf "  ${C_YELLOW}${C_BOLD}⚡${C_RESET}  $*\n"; }
fail() { printf "  ${C_RED}${C_BOLD}✖${C_RESET}  $*\n"; }
info() { printf "  ${C_CYAN}${C_BOLD}●${C_RESET}  $*\n"; }
step() { printf "\n  ${C_MAGENTA}${C_BOLD}▶ $*${C_RESET}\n"; }

WORKSPACE="${ROS2_WS:-${HOME}/ultrasonic}"

# ── Banner ─────────────────────────────────────────────────────────────────────
clear
print_dline
printf "\n"
printf "  ${C_CYAN}${C_BOLD}   📏  ULTRASONIC  ·  MEASURE CLIENT${C_RESET}\n"
printf "  ${C_DIM}   On-demand single distance readings${C_RESET}\n"
printf "  ${C_DIM}   Created by Dilip Kumar${C_RESET}\n"
printf "\n"
print_dline

# ── Environment ────────────────────────────────────────────────────────────────
step "Environment"
print_line

if [[ -z "${ROS_DISTRO:-}" ]]; then
    SETUP_FILE="${WORKSPACE}/install/setup.bash"
    [[ -f "$SETUP_FILE" ]] || SETUP_FILE="/opt/ros/humble/setup.bash"
    if [[ -f "$SETUP_FILE" ]]; then
        # shellcheck source=/dev/null
        source "$SETUP_FILE"
        ok "Sourced → ${C_DIM}${SETUP_FILE}${C_RESET}"
    else
        fail "ROS 2 environment not found!"
        exit 1
    fi
else
    ok "ROS 2 ${C_BOLD}${ROS_DISTRO}${C_RESET} active"
fi

# Check ultrasonic_node is running
if ros2 node list 2>/dev/null | grep -q "ultrasonic_node"; then
    ok "ultrasonic_node is ${C_GREEN}${C_BOLD}running${C_RESET}"
else
    warn "ultrasonic_node is ${C_YELLOW}${C_BOLD}not detected${C_RESET}"
    warn "Start it first:  ${C_BOLD}./scripts/launch.sh${C_RESET}"
    printf "\n"
    printf "  ${C_DIM}Continuing anyway — client will wait for data …${C_RESET}\n"
fi

# Check topic
if ros2 topic list 2>/dev/null | grep -q "/ultrasonic/range"; then
    ok "Topic ${C_BOLD}/ultrasonic/range${C_RESET} is ${C_GREEN}active${C_RESET}"
else
    warn "Topic ${C_BOLD}/ultrasonic/range${C_RESET} not yet visible"
fi

# ── Usage card ────────────────────────────────────────────────────────────────
printf "\n"
print_dline
printf "\n"
printf "  ${C_WHITE}${C_BOLD}Commands inside the client:${C_RESET}\n\n"
printf "    ${C_CYAN}${C_BOLD}m${C_RESET} ${C_DIM}or${C_RESET} ${C_CYAN}${C_BOLD}measure${C_RESET}   →  Take one distance reading\n"
printf "    ${C_CYAN}${C_BOLD}q${C_RESET} ${C_DIM}or${C_RESET} ${C_CYAN}${C_BOLD}quit${C_RESET}     →  Exit\n"
printf "    ${C_CYAN}${C_BOLD}Ctrl+C${C_RESET}          →  Force quit\n"
printf "\n"
printf "  ${C_DIM}Distance zones:${C_RESET}\n"
printf "    ${C_RED}${C_BOLD}●${C_RESET}  ${C_RED}Danger ${C_RESET} ${C_DIM}< 30 cm${C_RESET}\n"
printf "    ${C_YELLOW}${C_BOLD}●${C_RESET}  ${C_YELLOW}Caution${C_RESET} ${C_DIM}30 – 100 cm${C_RESET}\n"
printf "    ${C_GREEN}${C_BOLD}●${C_RESET}  ${C_GREEN}Safe   ${C_RESET} ${C_DIM}> 100 cm${C_RESET}\n"
printf "\n"
print_dline
printf "\n"
printf "  ${C_GREEN}${C_BOLD}🚀 Starting measure_client …${C_RESET}\n\n"

# ── Launch ─────────────────────────────────────────────────────────────────────
exec ros2 run ultrasonic measure_client
