"""Pencatatan input dan output eksperimen ke CSV."""

import csv
from datetime import datetime
from pathlib import Path


CSV_FIELDS = [
    "timestamp", "start", "goal", "vehicle_code", "vehicle_name", "km_per_liter",
    "fuel_code", "fuel_name", "fuel_price_per_liter", "service_code", "service_name",
    "distance_weight", "time_weight", "route", "total_distance_km", "total_time_minutes",
    "fuel_cost", "final_score", "status"
]


def append_experiment(output_path, inputs, result):
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    file_exists = output_path.exists() and output_path.stat().st_size > 0
    row = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        **inputs,
        "route": " -> ".join(result["path"]) if result else "",
        "total_distance_km": f"{result['distance']:.2f}" if result else "",
        "total_time_minutes": f"{result['time']:.1f}" if result else "",
        "fuel_cost": f"{result['fuel_cost']:.2f}" if result else "",
        "final_score": f"{result['score']:.12f}" if result else "",
        "status": "FOUND" if result else "NOT_FOUND"
    }
    with output_path.open("a", newline="", encoding="utf-8-sig") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=CSV_FIELDS)
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)
