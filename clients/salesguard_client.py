"""
Пример интеграции SalesGuard с ExperimentHub через DiD.
Передаёт продажи SKU до/после акции и контрольную группу.
"""
import requests

EH_BASE = "http://localhost:8001"

def run_promotion_did(
    sku_sales_before: list[float],
    sku_sales_after: list[float],
    control_sales_before: list[float],
    control_sales_after: list[float]
) -> dict:
    """Оценить чистый эффект акции через DiD."""
    r = requests.post(f"{EH_BASE}/quasi/did", json={
        "treatment_before": sku_sales_before,
        "treatment_after": sku_sales_after,
        "control_before": control_sales_before,
        "control_after": control_sales_after
    })
    return r.json()
