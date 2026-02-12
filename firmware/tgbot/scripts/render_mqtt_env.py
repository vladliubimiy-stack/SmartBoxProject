#!/usr/bin/env python3
"""Render runtime MQTT env file with current host IP."""

from __future__ import annotations

import argparse
import ipaddress
import os
import re
import socket
import subprocess
import sys
from pathlib import Path

DEFAULT_PORT = 1883


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Определяет IPv4 адрес интерфейса и рендерит runtime .env для Telegram-бота."
    )
    parser.add_argument(
        "--iface",
        default=os.getenv("MQTT_BIND_IFACE", "").strip() or None,
        help=(
            "Имя интерфейса (например wlan0/eth0 на Linux или 'Ethernet 2' на Windows). "
            "Если не задано, используется интерфейс маршрута по умолчанию (Linux) "
            "или fallback-определение (Windows/macOS)."
        ),
    )
    parser.add_argument(
        "--output",
        default=str(Path(__file__).resolve().parents[1] / ".env.runtime"),
        help="Путь к runtime env-файлу (по умолчанию tgbot/.env.runtime).",
    )
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help=f"MQTT порт (по умолчанию {DEFAULT_PORT}).")
    return parser.parse_args()


def run_ip_command(args: list[str]) -> str:
    result = subprocess.run(["ip", *args], check=True, text=True, capture_output=True)
    return result.stdout


def _decode_windows_output(raw: bytes) -> str:
    for enc in ("cp866", "cp1251", "utf-8"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="ignore")


def run_ipconfig() -> str:
    result = subprocess.run(["ipconfig"], check=True, capture_output=True)
    return _decode_windows_output(result.stdout)


def default_iface_linux() -> str | None:
    output = run_ip_command(["-4", "route", "show", "default"])
    match = re.search(r"\bdev\s+(\S+)", output)
    return match.group(1) if match else None


def iface_ipv4_linux(iface: str) -> str | None:
    output = run_ip_command(["-4", "-o", "addr", "show", "dev", iface])
    for line in output.splitlines():
        match = re.search(r"\binet\s+(\d+\.\d+\.\d+\.\d+)/", line)
        if not match:
            continue
        ip_str = match.group(1)
        if not ipaddress.ip_address(ip_str).is_loopback:
            return ip_str
    return None


def first_non_loopback_ipv4_linux() -> tuple[str, str] | None:
    output = run_ip_command(["-4", "-o", "addr", "show"])
    for line in output.splitlines():
        match = re.search(r"^\d+:\s+([^\s]+)\s+inet\s+(\d+\.\d+\.\d+\.\d+)/", line)
        if not match:
            continue
        iface, ip_str = match.group(1), match.group(2)
        if iface == "lo" or ipaddress.ip_address(ip_str).is_loopback:
            continue
        return iface, ip_str
    return None


def parse_windows_interfaces(ipconfig_output: str) -> list[tuple[str, str]]:
    """Extract (interface_name, ipv4) from ipconfig output (EN/RU Windows)."""
    interfaces: list[tuple[str, str]] = []
    current_iface: str | None = None

    for raw_line in ipconfig_output.splitlines():
        line = raw_line.rstrip()
        if not line.strip():
            continue

        # Interface header usually ends with ':' and does not start with whitespace.
        if not line.startswith((" ", "\t")) and line.endswith(":"):
            header = line[:-1].strip()
            # ex: "Ethernet adapter Ethernet 2"
            # ex (ru): "Адаптер Ethernet Ethernet 2"
            current_iface = re.sub(r"^(Ethernet adapter|Wireless LAN adapter|Адаптер Ethernet|Адаптер беспроводной локальной сети)\s+", "", header, flags=re.IGNORECASE).strip()
            continue

        if current_iface:
            ip_match = re.search(r"(\d+\.\d+\.\d+\.\d+)", line)
            if not ip_match:
                continue
            ip_str = ip_match.group(1)
            try:
                ip_obj = ipaddress.ip_address(ip_str)
            except ValueError:
                continue
            if ip_obj.version == 4 and not ip_obj.is_loopback:
                # likely IPv4 line; avoid subnet mask/gateway duplicates by first hit per iface
                if not any(existing_iface == current_iface for existing_iface, _ in interfaces):
                    interfaces.append((current_iface, ip_str))

    return interfaces


def _normalize_iface_name(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"\s+", " ", value)
    value = re.sub(
        r"^(ethernet adapter|wireless lan adapter|адаптер ethernet|адаптер беспроводной локальной сети)\s+",
        "",
        value,
        flags=re.IGNORECASE,
    )
    return value.strip()


def iface_ipv4_windows(iface: str) -> str | None:
    output = run_ipconfig()
    requested = _normalize_iface_name(iface)
    for name, ip_str in parse_windows_interfaces(output):
        normalized_name = _normalize_iface_name(name)
        if normalized_name == requested:
            return ip_str
        if requested and (requested in normalized_name or normalized_name in requested):
            return ip_str
    return None


def first_non_loopback_ipv4_windows() -> tuple[str, str] | None:
    output = run_ipconfig()
    parsed = parse_windows_interfaces(output)
    return parsed[0] if parsed else None


def detect_ipv4_with_udp_probe() -> str | None:
    targets = [("8.8.8.8", 80), ("1.1.1.1", 80), ("192.168.0.1", 80)]
    for host, port in targets:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            sock.connect((host, port))
            ip_str = sock.getsockname()[0]
            if ip_str and not ipaddress.ip_address(ip_str).is_loopback:
                return ip_str
        except OSError:
            continue
        finally:
            sock.close()
    return None


def detect_ipv4_from_hostname() -> str | None:
    try:
        host_ips = socket.gethostbyname_ex(socket.gethostname())[2]
    except OSError:
        return None

    for ip_str in host_ips:
        try:
            ip_obj = ipaddress.ip_address(ip_str)
        except ValueError:
            continue
        if ip_obj.version == 4 and not ip_obj.is_loopback:
            return ip_str
    return None


def resolve_mqtt_host(requested_iface: str | None) -> tuple[str, str]:
    # Linux path if ip tool exists
    if os.name != "nt":
        try:
            subprocess.run(["ip", "-V"], check=True, capture_output=True, text=True)
            ip_available = True
        except (FileNotFoundError, subprocess.CalledProcessError):
            ip_available = False

        if ip_available:
            if requested_iface:
                ip_str = iface_ipv4_linux(requested_iface)
                if not ip_str:
                    raise RuntimeError(
                        f"Для интерфейса '{requested_iface}' не найден IPv4 адрес. "
                        "Проверьте MQTT_BIND_IFACE и состояние интерфейса."
                    )
                return requested_iface, ip_str

            routed_iface = default_iface_linux()
            if routed_iface:
                ip_str = iface_ipv4_linux(routed_iface)
                if ip_str:
                    return routed_iface, ip_str

            fallback = first_non_loopback_ipv4_linux()
            if fallback:
                return fallback

    # Windows path: honour explicit interface name from ipconfig
    if os.name == "nt":
        if requested_iface:
            ip_str = iface_ipv4_windows(requested_iface)
            if not ip_str:
                raise RuntimeError(
                    f"Для интерфейса Windows '{requested_iface}' не найден IPv4 адрес. "
                    "Проверьте имя адаптера (например 'Ethernet 2' или 'Адаптер Ethernet Ethernet 2') и MQTT_BIND_IFACE."
                )
            return requested_iface, ip_str

        fallback_win = first_non_loopback_ipv4_windows()
        if fallback_win:
            return fallback_win

    # universal fallback
    ip_str = detect_ipv4_with_udp_probe() or detect_ipv4_from_hostname()
    if ip_str:
        return requested_iface or "auto", ip_str

    raise RuntimeError(
        "Не удалось определить IPv4 адрес для MQTT_HOST. "
        "Укажите MQTT_BIND_IFACE (например wlan0/eth0/'Ethernet 2') или MQTT_HOST вручную."
    )


def render_env(output_path: Path, host: str, port: int, iface: str) -> None:
    content = (
        "# Auto-generated by tgbot/scripts/render_mqtt_env.py\n"
        f"# MQTT_BIND_IFACE={iface}\n"
        f"MQTT_HOST={host}\n"
        f"MQTT_PORT={port}\n"
    )
    output_path.write_text(content, encoding="utf-8")


def main() -> int:
    args = parse_args()
    output_path = Path(args.output)

    try:
        iface, host = resolve_mqtt_host(args.iface)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        render_env(output_path, host, args.port, iface)
        print(f"Runtime env written to {output_path} (iface={iface}, MQTT_HOST={host}, MQTT_PORT={args.port})")
        return 0
    except Exception as exc:
        print(f"[render_mqtt_env] ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
