import sys
sys.path.insert(0, '/app/app')
import numpy as np
from stats.frequentist import z_test_proportions

def run_aa_simulation(n_simulations=1000, n_per_variant=500, base_rate=0.10, alpha=0.05):
    """
    AA-тест: оба варианта одинаковые. Доля ложноположительных должна ≈ alpha.
    """
    false_positives = 0
    rng = np.random.default_rng(42)
    for _ in range(n_simulations):
        conv_a = int(rng.binomial(n_per_variant, base_rate))
        conv_b = int(rng.binomial(n_per_variant, base_rate))
        result = z_test_proportions(n_per_variant, conv_a, n_per_variant, conv_b, alpha)
        if result["significant"]:
            false_positives += 1
    fpr = false_positives / n_simulations
    print(f"AA-тест: {n_simulations} симуляций, alpha={alpha}")
    print(f"Ложноположительных: {false_positives} ({fpr:.3f})")
    print(f"Ожидаемо: ~{alpha} ± 0.015")
    assert abs(fpr - alpha) < 0.02, f"FPR {fpr} слишком далеко от alpha {alpha}"
    print("AA-тест пройден.")

if __name__ == "__main__":
    run_aa_simulation()
