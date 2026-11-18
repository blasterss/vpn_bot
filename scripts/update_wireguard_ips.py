#!/usr/bin/env python3
"""Update angristan's ALLOWED_IPS for newly generated client configs."""

import argparse
import fcntl
import ipaddress
import os
import re
import stat
import tempfile
from pathlib import Path
from urllib.request import urlopen

SOURCE_URL = (
    "https://gist.githubusercontent.com/iamwildtuna/"
    "7772b7c84a11bf6e1385f23096a73a15/raw/gistfile2.txt"
)
MAX_DOWNLOAD_BYTES = 10 * 1024 * 1024
IP_PATTERN = re.compile(r"(?<![\w.])(?:[0-9]{1,3}\.){3}[0-9]{1,3}(?:/[0-9]+)?(?![\w./])")
ALLOWED_PATTERN = re.compile(r"^ALLOWED_IPS=.*$", re.MULTILINE)


def parse_addresses(text: str) -> list[str]:
    networks = set()
    for line in text.splitlines():
        line = line.strip()
        if line.startswith(("#", "//")):
            continue
        if re.match(r"route\s+add\s", line, re.IGNORECASE):
            route = re.fullmatch(
                r"route\s+add\s+(\S+)\s+mask\s+(\S+)\s+(\S+)",
                line,
                re.IGNORECASE,
            )
            if route is None:
                raise ValueError(f"Некорректная строка route ADD: {line}")
            destination, mask, gateway = route.groups()
            ipaddress.IPv4Address(gateway)
            # Gateway and netmask are not destination routes.
            networks.add(ipaddress.IPv4Network(f"{destination}/{mask}", strict=False))
            continue
        for match in IP_PATTERN.finditer(line):
            networks.add(ipaddress.IPv4Network(match.group(), strict=False))
    if not networks:
        raise ValueError("Список не содержит IPv4-адресов")
    return [str(network) for network in ipaddress.collapse_addresses(networks)]


def download_addresses(url: str) -> list[str]:
    if not url.startswith("https://"):
        raise ValueError("Источник должен использовать HTTPS")
    with urlopen(url, timeout=30) as response:
        if not response.geturl().startswith("https://"):
            raise ValueError("Перенаправление на источник без HTTPS")
        content = response.read(MAX_DOWNLOAD_BYTES + 1)
    if len(content) > MAX_DOWNLOAD_BYTES:
        raise ValueError("Список превышает 10 MiB")
    return parse_addresses(content.decode("utf-8-sig"))


def update_params(params: Path, addresses: list[str]) -> bool:
    """Replace only ALLOWED_IPS, preserving permissions and ownership."""
    if not addresses:
        raise ValueError("Нельзя записать пустой список")
    # Validate again so this entry point cannot write arbitrary shell expressions.
    allowed_ips = ",".join(sorted({str(ipaddress.IPv4Network(ip)) for ip in addresses}))
    with params.with_name(params.name + ".ips-update.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        if params.is_symlink():
            raise ValueError("Файл params не должен быть символической ссылкой")
        metadata = params.stat()
        original = params.read_text()
        if len(ALLOWED_PATTERN.findall(original)) != 1:
            raise ValueError("В params должна быть ровно одна строка ALLOWED_IPS=")
        updated = ALLOWED_PATTERN.sub(f"ALLOWED_IPS={allowed_ips}", original)
        if updated == original:
            return False
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(mode="w", dir=params.parent, delete=False) as output:
                temporary = Path(output.name)
                os.fchown(output.fileno(), metadata.st_uid, metadata.st_gid)
                os.fchmod(output.fileno(), stat.S_IMODE(metadata.st_mode))
                output.write(updated)
                output.flush()
                os.fsync(output.fileno())
            os.replace(temporary, params)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
    return True


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default=os.environ.get("SOURCE_URL") or SOURCE_URL)
    parser.add_argument("--params", type=Path, default=Path("/etc/wireguard/params"))
    args = parser.parse_args()
    try:
        addresses = download_addresses(args.url)
        changed = update_params(args.params, addresses)
    except (OSError, ValueError) as exc:
        parser.exit(1, f"Обновление не выполнено: {exc}\n")
    print(f"{'Обновлено' if changed else 'Без изменений'}: {len(addresses)} IPv4-сетей")


if __name__ == "__main__":
    main()
