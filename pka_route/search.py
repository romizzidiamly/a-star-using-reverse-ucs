"""Algoritme pencarian rute A*."""

import heapq
from itertools import count

from .data import GRAPH, DISTANCE
from .metrics import (
    build_normalization_constants,
    calculate_effective_distance,
    calculate_g_score,
    edge_metrics,
)


def reverse_ucs_lower_bounds(goal, metric_fn):
    """Menghitung exact shortest-path lower bound dari setiap node ke goal."""

    reverse_graph = {node: {} for node in GRAPH}

    for node, neighbors in GRAPH.items():
        for neighbor, travel_time in neighbors.items():
            cost = metric_fn(node, neighbor, travel_time)

            reverse_graph[node][neighbor] = cost
            reverse_graph[neighbor][node] = cost

    distances = {
        node: float("inf")
        for node in GRAPH
    }

    distances[goal] = 0.0

    queue = [(0.0, goal)]

    while queue:

        current_cost, current = heapq.heappop(queue)

        if current_cost > distances[current]:
            continue

        for neighbor, edge_cost in reverse_graph[current].items():

            candidate = current_cost + edge_cost

            if candidate < distances[neighbor]:

                distances[neighbor] = candidate

                heapq.heappush(
                    queue,
                    (candidate, neighbor)
                )

    return distances


def build_admissible_heuristic(
    goal,
    weights,
    norm,
    fuel_price_km
):
    """Membangun heuristic admissible berdasarkan distance dan time.

    Distance menggunakan DISTANCE aktual.
    Time menggunakan GRAPH aktual.

    Tidak menggunakan Euclidean distance dari COORDINATES.
    """

    distance_lb = reverse_ucs_lower_bounds(
        goal,
        lambda u, v, _time: calculate_effective_distance(
            DISTANCE[u][v],
            DISTANCE[u][v] * fuel_price_km
        )
    )

    time_lb = reverse_ucs_lower_bounds(
        goal,
        lambda _u, _v, travel_time: travel_time
    )

    def heuristic(node):

        return (
            weights["J_W"]
            * (distance_lb[node] / norm["D_SCALE"])
            +
            weights["W_W"]
            * (time_lb[node] / norm["T_SCALE"])
        )

    return heuristic


def reconstruct_path(came_from, current):

    path = [current]

    while current in came_from:

        current = came_from[current]
        path.append(current)

    return list(reversed(path))


def a_star_search_traced(
    start,
    goal,
    vehicle,
    fuel_type,
    service_type
):
    """A* search dengan trace untuk visualisasi."""

    weights = service_type[1]

    fuel_price_km = (
        fuel_type[1] / vehicle[1]
    )

    norm = build_normalization_constants(
        fuel_price_km
    )

    heuristic = build_admissible_heuristic(
        goal,
        weights,
        norm,
        fuel_price_km
    )

    g_score = {
        node: float("inf")
        for node in GRAPH
    }

    g_score[start] = 0.0

    came_from = {}

    closed_set = set()

    metrics = {
        start: (0.0, 0.0, 0.0)
    }

    tie_breaker = count()

    queue = [
        (
            heuristic(start),
            next(tie_breaker),
            start
        )
    ]

    steps = []

    step_num = 0

    result_path = None

    while queue:

        f_value, _, current = heapq.heappop(queue)

        if (
            f_value
            > g_score[current]
            + heuristic(current)
            + 1e-12
            or current in closed_set
        ):
            continue

        distance, total_time, fuel_cost = metrics[current]

        step_num += 1

        path_so_far = reconstruct_path(
            came_from,
            current
        )

        h_val = heuristic(current)

        steps.append({
            "step": step_num,
            "action": "expand",
            "node": current,
            "g": round(g_score[current], 6),
            "h": round(h_val, 6),
            "f": round(f_value, 6),
            "path_so_far": path_so_far,
            "distance": round(distance, 2),
            "time": round(total_time, 1),
            "fuel_cost": round(fuel_cost, 2),
            "parent": came_from.get(current),
            "improved": True,
        })

        if current == goal:

            result_path = path_so_far

            break

        closed_set.add(current)

        for neighbor in GRAPH[current]:

            if neighbor in closed_set:
                continue

            (
                segment_distance,
                segment_time,
                segment_fuel
            ) = edge_metrics(
                current,
                neighbor,
                fuel_price_km
            )

            new_metrics = (
                distance + segment_distance,
                total_time + segment_time,
                fuel_cost + segment_fuel
            )

            new_g = calculate_g_score(
                new_metrics[0],
                new_metrics[1],
                new_metrics[2],
                weights,
                norm
            )

            improved = (
                new_g < g_score[neighbor]
            )

            h_child = heuristic(neighbor)

            f_child = new_g + h_child

            step_num += 1

            if improved:

                neighbor_path = (
                    reconstruct_path(
                        came_from,
                        current
                    )
                    + [neighbor]
                )

            elif neighbor in came_from:

                neighbor_path = reconstruct_path(
                    came_from,
                    neighbor
                )

            else:

                neighbor_path = (
                    path_so_far
                    + [neighbor]
                )

            steps.append({
                "step": step_num,
                "action": "neighbor",
                "node": neighbor,
                "g": (
                    round(new_g, 6)
                    if improved
                    else round(
                        g_score[neighbor],
                        6
                    )
                ),
                "h": round(h_child, 6),
                "f": (
                    round(f_child, 6)
                    if improved
                    else round(
                        g_score[neighbor]
                        + h_child,
                        6
                    )
                ),
                "path_so_far": neighbor_path,
                "distance": (
                    round(new_metrics[0], 2)
                    if improved
                    else round(
                        metrics[neighbor][0],
                        2
                    )
                ),
                "time": (
                    round(new_metrics[1], 1)
                    if improved
                    else round(
                        metrics[neighbor][1],
                        1
                    )
                ),
                "fuel_cost": (
                    round(new_metrics[2], 2)
                    if improved
                    else round(
                        metrics[neighbor][2],
                        2
                    )
                ),
                "parent": (
                    current
                    if improved
                    else came_from.get(neighbor)
                ),
                "improved": improved,
            })

            if improved:

                came_from[neighbor] = current

                g_score[neighbor] = new_g

                metrics[neighbor] = new_metrics

                heapq.heappush(
                    queue,
                    (
                        f_child,
                        next(tie_breaker),
                        neighbor
                    )
                )

    if result_path is None:

        return {
            "steps": steps,
            "error": "No path found"
        }

    return {
        "steps": steps,
        "path": result_path,
        "distance": metrics[goal][0],
        "time": metrics[goal][1],
        "fuel_cost": metrics[goal][2],
        "score": g_score[goal],
        "normalization": norm,
    }


def a_star_search(
    start,
    goal,
    vehicle,
    fuel_type,
    service_type
):
    """A* search versi console."""

    print("\n" + "=" * 80)

    print(
        f" LOG PENCARIAN RUTE A* "
        f"({start} -> {goal})"
    )

    print("-" * 80)

    print(
        f" Kendaraan : {vehicle[0]} "
        f"(Konsumsi: {vehicle[1]} km/L)"
    )

    print(
        f" Bensin    : {fuel_type[0]} "
        f"(Rp{fuel_type[1]}/Liter)"
    )

    print(
        f" Layanan   : {service_type[0]}"
    )

    print("=" * 80)

    weights = service_type[1]

    fuel_price_km = (
        fuel_type[1] / vehicle[1]
    )

    norm = build_normalization_constants(
        fuel_price_km
    )

    heuristic = build_admissible_heuristic(
        goal,
        weights,
        norm,
        fuel_price_km
    )

    g_score = {
        node: float("inf")
        for node in GRAPH
    }

    g_score[start] = 0.0

    came_from = {}

    closed_set = set()

    metrics = {
        start: (0.0, 0.0, 0.0)
    }

    tie_breaker = count()

    queue = [
        (
            heuristic(start),
            next(tie_breaker),
            start
        )
    ]

    step = 1

    while queue:

        f_value, _, current = heapq.heappop(queue)

        if (
            f_value
            > g_score[current]
            + heuristic(current)
            + 1e-12
            or current in closed_set
        ):
            continue

        distance, total_time, fuel_cost = metrics[current]

        print(
            f"\n[LANGKAH {step}] "
            f"Ekspansi Node: '{current}'"
        )

        print(
            f"  > Path sementara: "
            f"{' -> '.join(reconstruct_path(came_from, current))}"
        )

        print(
            f"  > g(n) = {g_score[current]:.6f} "
            f"| h(n) = {heuristic(current):.6f} "
            f"| f(n) = {f_value:.6f}"
        )

        print(
            f"  > Metrics: "
            f"Jarak = {distance:.2f} km "
            f"| Waktu = {total_time:.1f} mnt "
            f"| Bensin = Rp{fuel_cost:.2f}"
        )

        if current == goal:

            return {
                "path": reconstruct_path(
                    came_from,
                    current
                ),
                "distance": distance,
                "time": total_time,
                "fuel_cost": fuel_cost,
                "score": g_score[current],
                "normalization": norm
            }

        closed_set.add(current)

        for neighbor in GRAPH[current]:

            if neighbor in closed_set:
                continue

            (
                segment_distance,
                segment_time,
                segment_fuel
            ) = edge_metrics(
                current,
                neighbor,
                fuel_price_km
            )

            new_metrics = (
                distance + segment_distance,
                total_time + segment_time,
                fuel_cost + segment_fuel
            )

            new_g = calculate_g_score(
                new_metrics[0],
                new_metrics[1],
                new_metrics[2],
                weights,
                norm
            )

            if new_g < g_score[neighbor]:

                came_from[neighbor] = current

                g_score[neighbor] = new_g

                metrics[neighbor] = new_metrics

                h_child = heuristic(neighbor)

                f_child = (
                    new_g + h_child
                )

                heapq.heappush(
                    queue,
                    (
                        f_child,
                        next(tie_breaker),
                        neighbor
                    )
                )

                print(
                    f"    - Ke '{neighbor}': "
                    f"g_child={new_g:.6f}, "
                    f"h_child={h_child:.6f}, "
                    f"f_child={f_child:.6f}"
                )

        step += 1

    return None