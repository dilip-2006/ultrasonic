#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────────────────
#  🔊  Ultrasonic ROS 2 — Professional Launcher
#      HC-SR04 · Arduino Nano · ROS 2 Humble · RViz2
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
C_BLUE='\033[94m'
C_MAGENTA='\033[95m'
C_WHITE='\033[97m'
C_BG_DARK='\033[40m'

# ── Helpers ────────────────────────────────────────────────────────────────────
print_line() { printf "${C_DIM}${C_CYAN}%s${C_RESET}\n" "$(printf '─%.0s' {1..64})"; }
print_dline(){ printf "${C_CYAN}${C_BOLD}%s${C_RESET}\n" "$(printf '═%.0s' {1..64})"; }

ok()   { printf "  ${C_GREEN}${C_BOLD}✔${C_RESET}  $*\n"; }
warn() { printf "  ${C_YELLOW}${C_BOLD}⚡${C_RESET}  $*\n"; }
fail() { printf "  ${C_RED}${C_BOLD}✖${C_RESET}  $*\n"; }
info() { printf "  ${C_CYAN}${C_BOLD}●${C_RESET}  $*\n"; }
step() { printf "\n  ${C_MAGENTA}${C_BOLD}▶ $*${C_RESET}\n"; }

spinner() {
    local pid=$1 msg=$2
    local frames=('⠋' '⠙' '⠹' '⠸' '⠼' '⠴' '⠦' '⠧' '⠇' '⠏')
    local i=0
    while kill -0 "$pid" 2>/dev/null; do
        printf "\r  ${C_CYAN}${frames[$((i % 10))]}${C_RESET}  ${C_DIM}%s${C_RESET}   " "$msg"
        sleep 0.1
        ((i++))
    done
    printf "\r%-60s\r" " "
}

# ── Banner ─────────────────────────────────────────────────────────────────────
clear
print_dline
printf "${C_CYAN}${C_BOLD}"
cat << 'EOF'
  ██╗   ██╗██╗  ████████╗██████╗  █████╗ ███████╗ ██████╗ ███╗   ██╗██╗ ██████╗
  ██║   ██║██║  ╚══██╔══╝██╔══██╗██╔══██╗██╔════╝██╔═══██╗████╗  ██║██║██╔════╝
  ██║   ██║██║     ██║   ██████╔╝███████║███████╗██║   ██║██╔██╗ ██║██║██║
  ██║   ██║██║     ██║   ██╔══██╗██╔══██║╚════██║██║   ██║██║╚██╗██║██║██║
  ╚██████╔╝███████╗██║   ██║  ██║██║  ██║███████║╚██████╔╝██║ ╚████║██║╚██████╗
   ╚═════╝ ╚══════╝╚═╝   ╚═╝  ╚═╝╚═╝  ╚═╝╚══════╝ ╚═════╝ ╚═╝  ╚═══╝╚═╝ ╚═════╝
EOF
printf "${C_RESET}"
printf "  ${C_DIM}HC-SR04 · Arduino Nano · ROS 2 Humble · RViz2${C_RESET}\n"
printf "  ${C_DIM}Created by Dilip Kumar${C_RESET}\n"
print_dline
printf "\n"

# ── Config ─────────────────────────────────────────────────────────────────────
SERIAL_PORT="${SERIAL_PORT:-/dev/ttyUSB0}"
BAUD_RATE="${BAUD_RATE:-115200}"
FRAME_ID="${FRAME_ID:-ultrasonic_link}"
PARENT_FRAME="${PARENT_FRAME:-base_link}"
WORKSPACE="${ROS2_WS:-${HOME}/ultrasonic}"

# Parse args
while [[ $# -gt 0 ]]; do
    case "$1" in
        --port)       SERIAL_PORT="$2"; shift 2 ;;
        --baud)       BAUD_RATE="$2";   shift 2 ;;
        --ws)         WORKSPACE="$2";   shift 2 ;;
        -h|--help)
            printf "  Usage: %s [OPTIONS]\n\n" "$(basename "$0")"
            printf "  Options:\n"
            printf "    --port  <path>   Serial port  (default: /dev/ttyUSB0)\n"
            printf "    --baud  <rate>   Baud rate    (default: 115200)\n"
            printf "    --ws    <path>   ROS2 workspace (default: ~/ultrasonic)\n"
            exit 0 ;;
        *) warn "Unknown argument: $1"; shift ;;
    esac
done

# ── Environment checks ─────────────────────────────────────────────────────────
step "Environment Checks"
print_line

# ROS 2 sourced?
if [[ -z "${ROS_DISTRO:-}" ]]; then
    SETUP_FILE="${WORKSPACE}/install/setup.bash"
    if [[ -f "$SETUP_FILE" ]]; then
        # shellcheck source=/dev/null
        source "$SETUP_FILE"
        ok "Workspace sourced → ${C_DIM}${SETUP_FILE}${C_RESET}"
    else
        SETUP_FILE="/opt/ros/humble/setup.bash"
        if [[ -f "$SETUP_FILE" ]]; then
            # shellcheck source=/dev/null
            source "$SETUP_FILE"
            ok "ROS 2 Humble sourced → ${C_DIM}${SETUP_FILE}${C_RESET}"
        else
            fail "ROS 2 not found!  Run: source /opt/ros/humble/setup.bash"
            exit 1
        fi
    fi
else
    ok "ROS 2 active  → distro ${C_BOLD}${ROS_DISTRO}${C_RESET}"
fi

# Python
PY_VER=$(python3 --version 2>&1 | awk '{print $2}')
ok "Python ${C_BOLD}${PY_VER}${C_RESET}"

# pyserial
if python3 -c "import serial" 2>/dev/null; then
    ok "pyserial available"
else
    warn "pyserial not found — installing …"
    pip install pyserial -q
    ok "pyserial installed"
fi

# Package present?
if ros2 pkg list 2>/dev/null | grep -q "^ultrasonic$"; then
    PKG_VER=$(python3 -c "
import xml.etree.ElementTree as ET, glob, os
pkgs=glob.glob('${WORKSPACE}/install/ultrasonic/**/package.xml', recursive=True)
if pkgs: print(ET.parse(pkgs[0]).findtext('version','?'))
" 2>/dev/null || echo "?")
    ok "ultrasonic package found  (v${PKG_VER})"
else
    warn "Package not found in index — attempting build …"
    print_line
    info "Running colcon build …"
    (cd "${WORKSPACE}" && colcon build --packages-select ultrasonic 2>&1) &
    BUILD_PID=$!
    spinner $BUILD_PID "Building ultrasonic …"
    wait $BUILD_PID
    # shellcheck source=/dev/null
    source "${WORKSPACE}/install/setup.bash"
    ok "Build complete"
    print_line
fi

# Serial port
printf "\n"
step "Hardware Check"
print_line

if [[ -e "${SERIAL_PORT}" ]]; then
    PERMS=$(stat -c "%a" "${SERIAL_PORT}" 2>/dev/null || echo "???")
    ok "Serial port found  → ${C_BOLD}${SERIAL_PORT}${C_RESET}  ${C_DIM}(perms ${PERMS})${C_RESET}"
    # Group check
    if ! groups | grep -q "dialout"; then
        warn "User not in 'dialout' group — may need: ${C_BOLD}sudo usermod -aG dialout \$USER${C_RESET}"
    fi
else
    # Look for alternatives
    ALTS=( $(ls /dev/ttyUSB* /dev/ttyACM* 2>/dev/null || true) )
    if [[ ${#ALTS[@]} -gt 0 ]]; then
        warn "Port ${SERIAL_PORT} not found.  Available: ${C_BOLD}${ALTS[*]}${C_RESET}"
        SERIAL_PORT="${ALTS[0]}"
        warn "Auto-selecting → ${C_BOLD}${SERIAL_PORT}${C_RESET}"
    else
        warn "No serial port detected.  Plug in your Arduino Nano."
        warn "Launching anyway — node will retry every 3 s."
    fi
fi

# ── Launch summary ─────────────────────────────────────────────────────────────
printf "\n"
step "Launch Configuration"
print_line
printf "  ${C_WHITE}%-18s${C_RESET}  %s\n"  "Serial Port"   "${C_CYAN}${SERIAL_PORT}${C_RESET}"
printf "  ${C_WHITE}%-18s${C_RESET}  %s\n"  "Baud Rate"     "${C_CYAN}${BAUD_RATE}${C_RESET}"
printf "  ${C_WHITE}%-18s${C_RESET}  %s\n"  "TF Frame"      "${C_CYAN}${FRAME_ID}${C_RESET}"
printf "  ${C_WHITE}%-18s${C_RESET}  %s\n"  "Parent Frame"  "${C_CYAN}${PARENT_FRAME}${C_RESET}"
printf "  ${C_WHITE}%-18s${C_RESET}  %s\n"  "ROS Distro"    "${C_CYAN}${ROS_DISTRO:-humble}${C_RESET}"
printf "\n"
printf "  ${C_DIM}Topics published:${C_RESET}\n"
printf "    ${C_GREEN}▸${C_RESET}  /ultrasonic/range       → ${C_DIM}sensor_msgs/Range${C_RESET}\n"
printf "    ${C_GREEN}▸${C_RESET}  /ultrasonic/distance_m  → ${C_DIM}std_msgs/Float32${C_RESET}\n"
printf "    ${C_GREEN}▸${C_RESET}  /ultrasonic/markers     → ${C_DIM}visualization_msgs/MarkerArray${C_RESET}\n"
printf "\n"
printf "  ${C_DIM}TF:  base_link → ultrasonic_link${C_RESET}\n"
print_line

# ── Countdown ─────────────────────────────────────────────────────────────────
printf "\n"
for i in 3 2 1; do
    printf "\r  ${C_YELLOW}${C_BOLD}Launching in  ${i} …${C_RESET}   "
    sleep 1
done
printf "\r%-60s\r" " "

printf "  ${C_GREEN}${C_BOLD}🚀 Launching ultrasonic nodes …${C_RESET}\n\n"
print_dline
printf "\n"

# ── Hand off to ROS 2 ─────────────────────────────────────────────────────────
exec ros2 launch ultrasonic ultrasonic_launch.py \
    serial_port:="${SERIAL_PORT}" \
    baud_rate:="${BAUD_RATE}" \
    frame_id:="${FRAME_ID}" \
    parent_frame:="${PARENT_FRAME}"
