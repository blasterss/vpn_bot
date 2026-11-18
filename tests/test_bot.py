import asyncio
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pexpect

from src import bot


class WireGuardTests(unittest.TestCase):
    def test_interactive_menu_and_default_addresses(self):
        # Real PTY + bash readline: verifies Enter preserves the proposed addresses.
        with tempfile.TemporaryDirectory() as directory:
            script = Path(directory) / "wireguard-install.sh"
            script.write_text("""#!/bin/bash
read -rp 'Select an option [1-5]: ' menu
[ "$menu" = 1 ] || exit 1
read -rp 'Client name: ' name
read -erp 'Client WireGuard IPv4: 10.66.66.' -i 2 ipv4
read -erp 'Client WireGuard IPv6: fd42:42:42::' -i 2 ipv6
[ "$ipv4" = 2 ] && [ "$ipv6" = 2 ] || exit 2
printf '[Interface]\\n' > "wg0-client-$name.conf"
""")
            script.chmod(0o700)
            real_spawn = pexpect.spawn

            def spawn_without_sudo(command, args, **kwargs):
                self.assertEqual((command, args), ("sudo", ["-n", str(script)]))
                return real_spawn("/bin/bash", [str(script)], **kwargs)

            with patch.multiple(
                bot,
                WORKING_DIR=directory,
                WIREGUARD_CONFIG_DIR=directory,
                WIREGUARD_SCRIPT_PATH=str(script),
                WIREGUARD_INTERFACE="wg0",
            ):
                with patch.object(bot.pexpect, "spawn", side_effect=spawn_without_sudo):
                    output = bot.create_wireguard_user("wg_123")
                self.assertEqual(Path(output).read_text(), "[Interface]\n")
                with self.assertRaises(ValueError):
                    bot.create_wireguard_user("client_name_over_15_characters")

    def test_missing_scripts(self):
        with patch.multiple(
            bot, SCRIPT_PATH="/missing/openvpn.sh", WIREGUARD_SCRIPT_PATH="/missing/wireguard.sh"
        ):
            with self.assertRaises(ValueError):
                asyncio.run(bot.create_vpn_user("client"))
            with self.assertRaises(ValueError):
                bot.create_wireguard_user("client")


class HandlerTests(unittest.IsolatedAsyncioTestCase):
    async def test_missing_protocol_does_not_start_subprocess(self):
        for command in ("/getopenvpn", "/getwireguard@my_bot"):
            message = SimpleNamespace(
                text=command,
                from_user=SimpleNamespace(username="test", id=1),
                answer=AsyncMock(),
                answer_document=AsyncMock(),
            )
            with patch.multiple(bot, SCRIPT_PATH=None, WIREGUARD_SCRIPT_PATH=None):
                await bot.cmd_vpn(message)
            self.assertIn("недоступен", message.answer.call_args.args[0].replace(" ", ""))
            message.answer_document.assert_not_awaited()

    async def test_openvpn_arguments(self):
        process = SimpleNamespace(communicate=AsyncMock(return_value=(b"", b"")), returncode=0)
        with tempfile.TemporaryDirectory() as directory:
            script = Path(directory) / "openvpn.sh"
            script.touch(mode=0o700)
            config = Path(directory) / "client.ovpn"
            config.write_text("config")
            with patch.multiple(bot, WORKING_DIR=directory, SCRIPT_PATH=str(script)):
                with patch.object(
                    bot.asyncio, "create_subprocess_exec", AsyncMock(return_value=process)
                ) as run:
                    self.assertEqual(await bot.create_vpn_user("client"), str(config))
                    self.assertEqual(
                        run.call_args.args, ("sudo", "-n", str(script), "client", "add", "client")
                    )
