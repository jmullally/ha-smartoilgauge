"""Check the Smart Oil Gauge login and show the raw tank data.

Run:  python tools/test_login.py
Prompts for your smartoilgauge.com login (password is not echoed or saved).
"""
import asyncio
import getpass
import importlib.util
import json
import pathlib
import sys

spec = importlib.util.spec_from_file_location(
    "sog_api",
    pathlib.Path(__file__).resolve().parent.parent / "custom_components" / "smartoilgauge" / "api.py",
)
api = importlib.util.module_from_spec(spec)
spec.loader.exec_module(api)


async def main() -> int:
    user = input("smartoilgauge.com username/email: ").strip()
    pw = getpass.getpass("password: ")
    client = api.SmartOilGaugeClient(user, pw)
    try:
        await client.login()
        tanks = await client.get_tanks()
    except api.SmartOilGaugeError as err:
        print(f"FAILED: {type(err).__name__}: {err}")
        return 1
    finally:
        await client.close()
    print(f"OK: {len(tanks)} tank(s)")
    print(json.dumps(tanks, indent=2))
    return 0


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    sys.exit(asyncio.run(main()))
