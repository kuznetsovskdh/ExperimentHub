import sys
sys.path.insert(0, '/app/app')
import numpy as np
from stats.cuped import apply_cuped, cuped_variance_reduction

def test_cuped_reduces_variance():
    rng = np.random.default_rng(42)
    n = 500
    # pre-период коррелирует с post (rho~0.7)
    pre = rng.normal(5, 2, n)
    noise = rng.normal(0, 1.5, n)
    post = 0.7 * pre + noise + rng.normal(0, 0.5, n)

    result = cuped_variance_reduction(post.tolist(), pre.tolist())
    print("CUPED:", result)
    assert result["reduction_pct"] > 10, "CUPED должен снижать дисперсию минимум на 10%"
    print("CUPED-тест пройден.")

if __name__ == "__main__":
    test_cuped_reduces_variance()
