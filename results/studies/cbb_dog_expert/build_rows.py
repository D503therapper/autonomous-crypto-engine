"""Build (or load) the 11/3 KNOWLEDGE (B) side table - the shared rows every cbb_dog_expert study reads."""
import importlib.util
import os
import time

OUT = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(OUT)))
_spec = importlib.util.spec_from_file_location("cbbk_lib", os.path.join(ROOT, "results/studies/cbb_knowledge_b/lib.py"))
K = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(K)

if __name__ == "__main__":
    t = time.time()
    rows = K.build()
    print(len(rows), "rows", round(time.time() - t), "s")
    print(sorted(rows[-1].keys()))
