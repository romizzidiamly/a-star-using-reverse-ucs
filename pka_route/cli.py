"""Antarmuka terminal aplikasi optimasi rute."""

from pathlib import Path

from .data import (
    FUEL_DATABASE,
    GRAPH,
    JUNCTION_NODES,
    SERVICE_DATABASE,
    VEHICLE_DATABASE,
)
from .logger import append_experiment
from .search import a_star_search


OUTPUT_CSV = Path(__file__).resolve().parent.parent / "output" / "eksperimen.csv"

LOCATION_NODES = [
    node for node in GRAPH
    if node not in JUNCTION_NODES
]


def format_summary(result, vehicle, fuel, service):
    """Menyusun baris ringkasan hasil optimasi rute.

    Dipakai oleh terminal sekaligus oleh pembuat screenshot agar isi keduanya
    tidak pernah berbeda.
    """

    if not result:

        return ["Status                : Rute Tidak Ditemukan."]

    return [
        "Rute Optimal          : " + " -> ".join(result["path"]),
        f"Kendaraan Digunakan   : {vehicle[0]} ({vehicle[1]} km/L)",
        f"Jenis BBM             : {fuel[0]}",
        f"Paket Layanan         : {service[0]}",
        f"Bobot Jarak (J_W)     : {service[1]['J_W']:.2f}",
        f"Bobot Waktu (W_W)     : {service[1]['W_W']:.2f}",
        f"Total Jarak           : {result['distance']:.2f} km",
        f"Total Waktu           : {result['time']:.1f} menit",
        f"Estimasi Biaya Bensin : Rp {result['fuel_cost']:.2f}",
    ]


def main():
    print("=" * 60)
    print(f" SISTEM OPTIMASI RUTE PENGIRIMAN MULTI-KRITERIA ({len(LOCATION_NODES)} LOKASI)")
    print("=" * 60)
    print("\nLokasi Tersedia:", ", ".join(sorted(LOCATION_NODES)))
    if JUNCTION_NODES:
        print("Persimpangan   :", ", ".join(sorted(JUNCTION_NODES)),
              "(boleh dipakai sebagai titik transit)")
    start = input("\nMasukkan Lokasi AWAL  (misal: A): ").strip().upper()
    goal = input("Masukkan Lokasi TUJUAN (misal: N): ").strip().upper()
    if start not in GRAPH or goal not in GRAPH:
        print("\n[ERROR] Lokasi awal atau tujuan tidak valid!")
        return

    print("\nPilih Jenis Kendaraan:")
    for key, (name, km_l) in VEHICLE_DATABASE.items():
        print(f" [{key}] {name} ({km_l} km/L)")
    vehicle_code = input("Masukkan pilihan kendaraan (1-4): ").strip()
    vehicle = VEHICLE_DATABASE.get(vehicle_code)

    print("\nPilih Jenis Bensin:")
    for key, (name, price) in FUEL_DATABASE.items():
        print(f" [{key}] {name} (Rp{price}/L)")
    fuel_code = input("Masukkan pilihan bensin (1-3): ").strip()
    fuel = FUEL_DATABASE.get(fuel_code)

    print("\nPilih Paket Layanan (Bobot Jarak & Waktu):")
    for key, (name, _) in SERVICE_DATABASE.items():
        print(f" [{key}] {name}")
    service_code = input("Masukkan pilihan layanan (1-4): ").strip()
    service = SERVICE_DATABASE.get(service_code)

    if not vehicle or not fuel or not service:
        print("\n[ERROR] Pilihan konfigurasi tidak valid!")
        return

    result = a_star_search(start, goal, vehicle, fuel, service)
    inputs = {
        "start": start, "goal": goal, "vehicle_code": vehicle_code, "vehicle_name": vehicle[0],
        "km_per_liter": vehicle[1], "fuel_code": fuel_code, "fuel_name": fuel[0],
        "fuel_price_per_liter": fuel[1], "service_code": service_code, "service_name": service[0],
        "distance_weight": service[1]["J_W"], "time_weight": service[1]["W_W"]
    }
    append_experiment(OUTPUT_CSV, inputs, result)

    print("\n" + "=" * 60)
    print(" RINGKASAN HASIL AKHIR OPTIMASI RUTE")
    print("=" * 60)
    for line in format_summary(result, vehicle, fuel, service):
        print(line)
    print(f"Data eksperimen disimpan ke: {OUTPUT_CSV}")
