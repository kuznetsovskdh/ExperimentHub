import sys
sys.path.insert(0, '/app/app')
import numpy as np
from stats.frequentist import z_test_proportions, t_test_continuous

def test_ab_detects_known_effect():
    """Синтетический AB: заданный эффект должен быть найден."""
    rng = np.random.default_rng(99)
    n = 2000

    # Пропорции: control 10%, treatment 14% — MDE 4pp
    conv_ctrl = int(rng.binomial(n, 0.10))
    conv_trt  = int(rng.binomial(n, 0.14))
    res = z_test_proportions(n, conv_ctrl, n, conv_trt)
    print("AB z-test:", res)
    assert res["significant"], "Z-test должен найти эффект 4pp при n=2000"

    # Непрерывная: treatment +1 единица
    ctrl = rng.normal(5, 2, n).tolist()
    trt  = rng.normal(6, 2, n).tolist()
    res2 = t_test_continuous(ctrl, trt)
    print("AB t-test:", res2)
    assert res2["significant"], "T-test должен найти эффект +1 при n=2000"

    print("Синтетический AB-тест пройден.")

if __name__ == "__main__":
    test_ab_detects_known_effect()
