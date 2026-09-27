"""Check the tennis game-spread lines parse from Bovada (runner)."""
import sys

sys.path.insert(0, ".")
import sports_tennis as st  # noqa: E402

lines = st.bovada()
with_sp = [ln for ln in lines if "a_hcp" in ln]
print(f"{len(lines)} matches priced, {len(with_sp)} with a game spread")
for ln in with_sp[:10]:
    print(f"   {ln['a']} {ln['a_ml']:+d} ({ln['a_hcp']:+g} games {ln['a_sp']:+d})  vs  {ln['b']} {ln['b_ml']:+d} ({ln['b_hcp']:+g} {ln['b_sp']:+d})")
