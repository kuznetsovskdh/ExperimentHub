import sys
sys.path.insert(0, '/app/app')
import numpy as np
from stats.frequentist import t_test_continuous
from stats.bootstrap import bootstrap_ci

def test_bootstrap_vs_ttest():
    rng = np.random.default_rng(42)
    n = 500
    ctrl = rng.normal(5, 2, n).tolist()
    trt  = rng.normal(6, 2, n).tolist()

    t_res = t_test_continuous(ctrl, trt)
    b_res = bootstrap_ci(ctrl, trt)

    print("T-test: ", t_res)
    print("Bootstrap:", b_res)

    # CI должны быть близки
    diff_lower = abs(t_res["ci_lower"] - b_res["ci_lower"])
    diff_upper = abs(t_res["ci_upper"] - b_res["ci_upper"])
    print(f"Расхождение CI: lower={diff_lower:.4f}, upper={diff_upper:.4f}")
    print("Оба значимы:", t_res["significant"], b_res["significant"])

    # При нормальных данных оба метода должны давать близкие CI
    assert diff_lower < 0.1 and diff_upper < 0.1, "CI сильно расходятся — проверь реализацию"
    print("Bootstrap-тест пройден.")

if __name__ == "__main__":
    test_bootstrap_vs_ttest()
