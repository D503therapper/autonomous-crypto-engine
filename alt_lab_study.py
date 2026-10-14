"""Owner 2026-10-14: "there's more crypto alt coins than just meme coins - go to the moon". Every lab strategy family
(rotation, breakout, dual momentum, trend ensemble, dip-buying ...) walk-forward on a WIDE altcoin list (~60 Crypto.com
coins: large caps + mid-cap alts + AI / gaming / L2 / DeFi), not just the 16 large coins tested before.
Params are re-picked on the prior 18 months and scored on the unseen next 6 (lab.run_market), vs hold BTC.
Run twice: Crypto.com-size fees (0.5%/side) and low maker fees (0.2%/side).

    python alt_lab_study.py --years 5
"""
import argparse

import config
import lab

ALTS = ["ETH", "SOL", "XRP", "ADA", "DOGE", "AVAX", "LINK", "DOT", "LTC", "BCH", "ATOM", "NEAR", "UNI", "AAVE", "SUI",
        "SHIB", "PEPE", "BONK", "WIF", "FLOKI", "TRX", "TON", "HBAR", "ICP", "FIL", "ETC", "XLM", "APT", "ARB", "OP",
        "INJ", "SEI", "TIA", "RNDR", "FET", "GRT", "IMX", "SAND", "MANA", "AXS", "GALA", "LDO", "MKR", "CRV", "SNX",
        "ALGO", "VET", "EGLD", "QNT", "RUNE", "KAS", "STX", "JUP", "PYTH", "ONDO", "ENA", "TAO", "WLD", "POL", "HYPE"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--years", type=int, default=5)
    ap.add_argument("--synthetic", action="store_true")
    a = ap.parse_args()
    lab.MARKET["crypto"]["syms"] = sorted(set(ALTS) | set(config.UNIVERSE))
    for cost in (0.005, 0.002):
        print(f"\n\n##### ALTCOINS, cost {cost:.1%} per side #####")
        lab.run_market("crypto", a.years, cost, a.synthetic)


if __name__ == "__main__":
    main()
