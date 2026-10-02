"""Perhitungan metrik rute dan fungsi objektif A*."""

from .data import DISTANCE, GRAPH


def get_distance(current, neighbor):
    """Mengambil jarak aktual antar-node."""
    try:
        return DISTANCE[current][neighbor]
    except KeyError:
        raise ValueError(
            f"Distance untuk edge {current} -> {neighbor} tidak ditemukan."
        )


def get_travel_time(current, neighbor):
    """Mengambil waktu tempuh aktual antar-node."""
    try:
        return GRAPH[current][neighbor]
    except KeyError:
        raise ValueError(
            f"Travel time untuk edge {current} -> {neighbor} tidak ditemukan."
        )


def calculate_fuel_cost(distance, fuel_price_km):
    """Menghitung biaya bahan bakar berdasarkan jarak."""
    return distance * fuel_price_km


def edge_metrics(current, neighbor, fuel_price_km):
    """Mengembalikan jarak, waktu, dan biaya bahan bakar edge."""

    distance = get_distance(current, neighbor)
    travel_time = get_travel_time(current, neighbor)

    fuel_cost = calculate_fuel_cost(
        distance,
        fuel_price_km
    )

    return distance, travel_time, fuel_cost


def calculate_effective_distance(distance, fuel_cost):
    """Menggabungkan jarak dan penalti biaya bahan bakar."""
    return distance + (fuel_cost / 1000.0)


def build_normalization_constants(fuel_price_km):
    """Menghitung konstanta normalisasi distance dan travel time."""

    max_effective_distance = 0.0
    max_time = 0.0

    for node, neighbors in GRAPH.items():

        for neighbor in neighbors:

            distance = get_distance(
                node,
                neighbor
            )

            travel_time = get_travel_time(
                node,
                neighbor
            )

            fuel_cost = calculate_fuel_cost(
                distance,
                fuel_price_km
            )

            effective_distance = calculate_effective_distance(
                distance,
                fuel_cost
            )

            max_effective_distance = max(
                max_effective_distance,
                effective_distance
            )

            max_time = max(
                max_time,
                travel_time
            )

    return {
        "D_SCALE": max(max_effective_distance, 1.0),
        "T_SCALE": max(max_time, 1.0),
    }


def calculate_g_score(
    distance,
    time,
    fuel_cost,
    weights,
    norm
):
    """Menghitung cumulative objective cost g(n)."""

    effective_distance = calculate_effective_distance(
        distance,
        fuel_cost
    )

    normalized_distance = (
        effective_distance /
        norm["D_SCALE"]
    )

    normalized_time = (
        time /
        norm["T_SCALE"]
    )

    return (
        weights["J_W"] * normalized_distance
        +
        weights["W_W"] * normalized_time
    )