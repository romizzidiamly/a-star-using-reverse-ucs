"""Penyusun ulang graf rute: sebar koordinat, kurangi edge, jadikan persimpangan node.

Tiga masalah pada data awal dan penanganannya di modul ini:

1. Koordinat antar node terlalu berdekatan (jarak terdekat hanya 1.41).
   Ditangani oleh ``initial_layout`` (gaya repulsif + pegas antar edge) yang
   menjaga jarak minimal :data:`MIN_SEPARATION` antar node.
2. Edge terlalu rapat (138 ruas, derajat rata-rata 10.6).
   Ditangani oleh ``prune_edges`` yang menyimpan spanning tree termurah lalu
   menambah ruas murah sampai ``:data:`TARGET_EDGES`` dengan batas derajat.
3. Ruas jalan saling menembus di titik potong.
   Ditangani oleh ``anneal_layout``/``stabilize_layout`` untuk menekan
   perpotongan, lalu ``create_junction_nodes`` menjadikan setiap titik potong
   yang tersisa menjadi node persimpangan yang dapat dilalui.

Jalankan ``python -m pka_route.graph_builder`` untuk menulis ulang
:mod:`pka_route.data` dari data mentah di bawah.
"""

import heapq
import itertools
import math
import random
from collections import defaultdict
from pathlib import Path


DATA_MODULE = Path(__file__).resolve().parent / "data.py"

DATABASE_MARKER = "VEHICLE_DATABASE = {"

CANVAS_WIDTH = 200.0

CANVAS_HEIGHT = 120.0

MIN_SEPARATION = 20.0

TARGET_EDGES = 40

MIN_DEGREE = 2

MAX_DEGREE = 4

MAX_DEGREE_TARGET = 18

DEGREE_SKEW = 1.8

SELECTION_NOISE = 0.8

EDGE_SEED = 2

EDGE_CAP = 45

CROSSING_WEIGHT = 60.0

LAYOUT_SEED = 0

LAYOUT_SEEDS = (0, 1, 2)

LAYOUT_ITERATIONS = 400

ANNEAL_SWEEPS = 700

CLEARANCE = 1.0

CLEARANCE_WEIGHT = 25.0

ON_EDGE_CLEARANCE = 1.2

ON_EDGE_WEIGHT = 60.0

JUNCTION_TOLERANCE = 1.5

MIN_SPLIT_FRACTION = 0.01

ON_EDGE_TOLERANCE = 0.5

DIRECTIONS = (
    (1.0, 0.0),
    (0.7071, 0.7071),
    (0.0, 1.0),
    (-0.7071, 0.7071),
    (-1.0, 0.0),
    (-0.7071, -0.7071),
    (0.0, -1.0),
    (0.7071, -0.7071),
)

SOURCE_COORDINATES = {

    "A": (0, 0), "B": (12, 25), "C": (5, 12), "D": (18, 21), "E": (12, 14),

    "F": (43, 10), "G": (17, 11), "H": (11, 28), "I": (44, 12), "J": (24, 24),

    "K": (1, 15), "L": (16, 16), "M": (11, 15), "N": (15, 27), "O": (19, 14),

    "P": (4, 25), "Q": (9, 23), "R": (13, 20), "S": (1, 22), "T": (42, 20),

    "U": (29, 7), "V": (34, 18), "W": (27, 28), "X": (36, 27),

    "Y": (22, 5), "Z": (48, 25)

}

SOURCE_GRAPH = {
    "A": {"C":112,"E":29,"J":26,"K":33,"L":20,"P":77,"U":102,"V":128,"W":16,"X":34,"Y":53},
    "B": {"F":40,"G":64,"H":26,"J":55,"K":64,"L":16,"O":70,"W":53,"Y":12},
    "C": {"A":112,"D":149,"G":136,"J":142,"K":131,"O":105,"P":139,"R":137,"S":80,"U":128,"V":51,"W":44,"Y":65},
    "D": {"C":149,"G":42,"H":65,"I":118,"L":12,"M":83,"N":137,"O":73,"S":84,"V":100,"Y":73},
    "E": {"A":29,"F":107,"G":118,"L":140,"M":23,"P":58,"R":99,"T":30,"Y":33},
    "F": {"B":40,"E":107,"L":43,"O":133,"S":105,"U":130,"V":148,"W":113,"X":66},
    "G": {"B":64,"C":136,"D":42,"E":118,"H":101,"M":140,"N":132,"O":127,"P":91,"Q":91,"R":54,"W":119},
    "H": {"B":26,"D":65,"G":101,"M":48,"Q":149,"R":149,"S":14,"W":127,"Y":110},
    "I": {"D":118,"L":144,"M":36,"N":32,"R":16,"T":149,"V":22,"W":147,"X":72,"Y":56,"Z":46},
    "J": {"A":26,"B":55,"C":142,"K":144,"N":30,"P":36,"Q":121,"S":84,"Y":41},
    "K": {"A":33,"B":64,"C":131,"J":144,"P":106,"Q":97,"S":72,"T":149,"V":22,"X":5,"Z":22},
    "L": {"A":20,"B":16,"D":12,"E":140,"F":43,"I":144,"T":99,"V":90,"W":80,"Y":43},
    "M": {"D":83,"E":23,"G":140,"H":48,"I":36,"P":79,"S":20,"T":11,"U":103,"V":55,"W":136,"Y":15,"Z":89},
    "N": {"D":137,"G":132,"I":32,"J":30,"P":37,"Q":140,"R":140,"S":110,"T":70,"W":27,"Y":6,"Z":148},
    "O": {"B":70,"C":105,"D":73,"F":133,"G":127,"W":77,"X":121,"Z":56},
    "P": {"A":77,"C":139,"E":58,"G":91,"J":36,"K":106,"M":79,"N":37,"Q":57,"R":115,"T":149,"W":75,"Y":18},
    "Q": {"G":91,"H":149,"J":121,"K":97,"N":140,"P":57,"U":74,"X":63,"Z":100},
    "R": {"C":137,"E":99,"G":54,"H":149,"I":16,"N":140,"P":115,"S":24,"V":52,"W":90,"X":120},
    "S": {"C":80,"D":84,"F":105,"H":14,"J":84,"K":72,"M":20,"N":110,"R":24,"T":51,"Z":72},
    "T": {"E":30,"I":149,"K":149,"L":99,"M":11,"N":70,"P":149,"S":51,"Z":53},
    "U": {"A":102,"C":128,"F":130,"M":103,"Q":74,"W":150,"X":81,"Y":147},
    "V": {"A":128,"C":51,"D":100,"F":148,"I":22,"K":22,"L":90,"M":55,"R":52,"X":52},
    "W": {"A":16,"B":53,"C":44,"F":113,"G":119,"H":127,"I":147,"L":80,"M":136,"N":27,"O":77,"P":75,"R":90,"U":150,"Y":142},
    "X": {"A":34,"F":66,"I":72,"K":5,"O":121,"Q":63,"R":120,"U":81,"V":52,"Y":105},
    "Y": {"A":53,"B":12,"C":65,"D":73,"E":33,"H":110,"I":56,"J":41,"L":43,"M":15,"N":6,"P":18,"U":147,"W":142,"X":105},
    "Z": {"I":46,"K":22,"M":89,"N":148,"O":56,"Q":100,"S":72,"T":53}
}

SOURCE_DISTANCE = {
    "A": {"C":23.1,"E":31.9,"J":4.5,"K":27.6,"L":18.5,"P":24.1,"U":12.6,"V":31.5,"W":7.2,"X":2.4,"Y":9.6},
    "B": {"F":27.5,"G":5.1,"H":15.5,"J":22.4,"K":12.0,"L":27.4,"O":33.6,"W":2.5,"Y":27.7},
    "C": {"A":23.1,"D":19.9,"G":6.4,"J":30.0,"K":19.1,"O":20.8,"P":18.0,"R":26.6,"S":26.9,"U":9.5,"V":5.1,"W":24.5,"Y":14.1},
    "D": {"C":19.9,"G":21.3,"H":17.4,"I":32.5,"L":5.9,"M":31.3,"N":26.8,"O":21.4,"S":12.1,"V":32.9,"Y":13.5},
    "E": {"A":31.9,"F":30.2,"G":29.7,"L":33.0,"M":2.4,"P":17.8,"R":30.6,"T":5.1,"Y":13.3},
    "F": {"B":27.5,"E":30.2,"L":26.4,"O":8.6,"S":20.5,"U":23.1,"V":5.6,"W":12.0,"X":18.6},
    "G": {"B":5.1,"C":6.4,"D":21.3,"E":29.7,"H":4.8,"M":5.3,"N":6.9,"O":2.3,"P":20.9,"Q":5.1,"R":30.3,"W":33.2},
    "H": {"B":15.5,"D":17.4,"G":4.8,"M":19.7,"Q":2.7,"R":26.1,"S":7.8,"W":15.5,"Y":24.0},
    "I": {"D":32.5,"L":14.6,"M":12.9,"N":28.0,"R":27.7,"T":25.6,"V":19.6,"W":17.2,"X":28.0,"Y":28.4,"Z":29.8},
    "J": {"A":4.5,"B":22.4,"C":30.0,"K":26.8,"N":6.6,"P":5.6,"Q":23.1,"S":16.8,"Y":27.4},
    "K": {"A":27.6,"B":12.0,"C":19.1,"J":26.8,"P":10.0,"Q":7.3,"S":23.7,"T":24.3,"V":27.7,"X":25.8,"Z":31.3},
    "L": {"A":18.5,"B":27.4,"D":5.9,"E":33.0,"F":26.4,"I":14.6,"T":24.2,"V":1.7,"W":33.4,"Y":23.0},
    "M": {"D":31.3,"E":2.4,"G":5.3,"H":19.7,"I":12.9,"P":29.4,"S":32.8,"T":7.5,"U":31.4,"V":6.1,"W":9.8,"Y":30.7,"Z":6.2},
    "N": {"D":26.8,"G":6.9,"I":28.0,"J":6.6,"P":28.8,"Q":8.0,"R":22.7,"S":34.1,"T":31.6,"W":20.9,"Y":19.3,"Z":34.0},
    "O": {"B":33.6,"C":20.8,"D":21.4,"F":8.6,"G":2.3,"W":5.2,"X":7.5,"Z":20.5},
    "P": {"A":24.1,"C":18.0,"E":17.8,"G":20.9,"J":5.6,"K":10.0,"M":29.4,"N":28.8,"Q":25.0,"R":4.1,"T":19.2,"W":12.2,"Y":10.6},
    "Q": {"G":5.1,"H":2.7,"J":23.1,"K":7.3,"N":8.0,"P":25.0,"U":17.5,"X":17.2,"Z":19.2},
    "R": {"C":26.6,"E":30.6,"G":30.3,"H":26.1,"I":27.7,"N":22.7,"P":4.1,"S":7.5,"V":33.3,"W":13.4,"X":2.7},
    "S": {"C":26.9,"D":12.1,"F":20.5,"H":7.8,"J":16.8,"K":23.7,"M":32.8,"N":34.1,"R":7.5,"T":9.6,"Z":5.5},
    "T": {"E":5.1,"I":25.6,"K":24.3,"L":24.2,"M":7.5,"N":31.6,"P":19.2,"S":9.6,"Z":7.7},
    "U": {"A":12.6,"C":9.5,"F":23.1,"M":31.4,"Q":17.5,"W":15.4,"X":24.5,"Y":32.9},
    "V": {"A":31.5,"C":5.1,"D":32.9,"F":5.6,"I":19.6,"K":27.7,"L":1.7,"M":6.1,"R":33.3,"X":20.1},
    "W": {"A":7.2,"B":2.5,"C":24.5,"F":12.0,"G":33.2,"H":15.5,"I":17.2,"L":33.4,"M":9.8,"N":20.9,"O":5.2,"P":12.2,"R":13.4,"U":15.4,"Y":24.0},
    "X": {"A":2.4,"F":18.6,"I":28.0,"K":25.8,"O":7.5,"Q":17.2,"R":2.7,"U":24.5,"V":20.1,"Y":22.1},
    "Y": {"A":9.6,"B":27.7,"C":14.1,"D":13.5,"E":13.3,"H":24.0,"I":28.4,"J":27.4,"L":23.0,"M":30.7,"N":19.3,"P":10.6,"U":32.9,"W":24.0,"X":22.1},
    "Z": {"I":29.8,"K":31.3,"M":6.2,"N":34.0,"O":20.5,"Q":19.2,"S":5.5,"T":7.7}
}


def _lookup(mapping, first, second):
    """Membaca nilai edge dari salah satu arah."""

    row = mapping.get(first, {})

    if second in row:
        return float(row[second])

    return float(mapping[second][first])


def label_index(name):
    """Mengubah nama node menjadi indeks berurutan (A=1 ... Z=26, AA=27)."""

    if len(name) == 1:
        return ord(name) - 64

    value = 0

    for character in name:
        value = value * 26 + (ord(character) - 64)

    return value


def label_from_index(index):
    """Membalik ``label_index`` ke nama node gaya spreadsheet."""

    letters = ""

    while index > 0:
        index, remainder = divmod(index - 1, 26)
        letters = chr(65 + remainder) + letters

    return letters


def unique_edges(graph, distance):
    """Mengumpulkan edge unik beserta waktu, jarak, dan biaya gabungannya."""

    times = [
        float(value)
        for neighbors in graph.values()
        for value in neighbors.values()
    ]

    distances = [
        float(value)
        for row in distance.values()
        for value in row.values()
    ]

    scale_time = max(times, default=1.0) or 1.0

    scale_distance = max(distances, default=1.0) or 1.0

    edges = {}

    for node, neighbors in graph.items():

        for neighbor in neighbors:

            key = (node, neighbor) if node <= neighbor else (neighbor, node)

            if key in edges:
                continue

            first, second = key

            minutes = _lookup(graph, first, second)

            kilometers = _lookup(distance, first, second)

            edges[key] = {
                "u": first,
                "v": second,
                "time": minutes,
                "distance": kilometers,
                "cost": (
                    0.5 * (kilometers / scale_distance)
                    + 0.5 * (minutes / scale_time)
                ),
            }

    return edges


def _minimum_spanning_tree(candidates):
    """Membangun spanning tree termurah sebagai penopang konektivitas."""

    adjacency = defaultdict(list)

    for edge in candidates.values():

        adjacency[edge["u"]].append(edge)
        adjacency[edge["v"]].append(edge)

    for row in adjacency.values():
        row.sort(key=lambda edge: edge["cost"])

    if not adjacency:
        return {}

    start = min(adjacency)

    in_tree = {start}

    kept = {}

    frontier = [
        (edge["cost"], edge["u"], edge["v"], position, edge)
        for position, edge in enumerate(adjacency[start])
    ]

    heapq.heapify(frontier)

    tie_breaker = len(frontier)

    while frontier:

        _cost, first, second, _position, edge = heapq.heappop(frontier)

        if first in in_tree and second in in_tree:
            continue

        kept[(edge["u"], edge["v"])] = edge

        in_tree.add(first)
        in_tree.add(second)

        for other in adjacency[second]:

            tie_breaker += 1

            heapq.heappush(frontier, (
                other["cost"],
                other["u"],
                other["v"],
                tie_breaker,
                other,
            ))

    return kept


def _degrees(kept):
    """Menghitung derajat tiap node dari daftar edge."""

    degrees = defaultdict(int)

    for edge in kept.values():
        degrees[edge["u"]] += 1
        degrees[edge["v"]] += 1

    return degrees


def sample_degree_targets(max_degree=MAX_DEGREE_TARGET, skew=DEGREE_SKEW, seed=EDGE_SEED):
    """Menyusun target derajat yang sengaja tidak seragam.

    Distribusi condong ke derajat kecil (``skew`` besar) sehingga sebagian node
    hanya tersambung ke satu jalan, sementara sebagian lain menjadi simpul
    dengan banyak cabang.
    """

    randomizer = random.Random(seed)

    targets = {}

    for node in SOURCE_COORDINATES:

        sample = randomizer.random()

        targets[node] = max(
            1,
            min(max_degree, 1 + int((max_degree - 1) * (sample ** skew)))
        )

    return targets


def select_edges(
    graph,
    distance,
    max_degree_target=MAX_DEGREE_TARGET,
    degree_skew=DEGREE_SKEW,
    selection_noise=SELECTION_NOISE,
    seed=EDGE_SEED,
    edge_cap=EDGE_CAP,
):
    """Memilih edge sehingga tiap node punya jumlah tetangga yang berbeda-beda.

    Berbeda dengan pemangkasan seragam, derajat tiap node tidak disamakan:
    node dengan target besar menjadi simpul banyak jalan, sedangkan node dengan
    target satu menjadi ujung jalan yang hanya punya satu akses.
    """

    candidates = unique_edges(graph, distance)

    targets = sample_degree_targets(max_degree_target, degree_skew, seed)

    randomizer = random.Random(seed + 991)

    pool = dict(candidates)

    scores = {
        identity: edge["cost"] * (
            1.0 + selection_noise * (randomizer.random() - 0.5)
        )
        for identity, edge in pool.items()
    }

    def key(edge):

        return scores[(edge["u"], edge["v"])]

    kept = _minimum_spanning_tree(candidates)

    degrees = _degrees(kept)

    # Tambahkan edge sesuai target derajat, simpul bertarget besar didahulukan
    # supaya daun yang ditiator tetap berdegree satu.
    for node in sorted(targets, key=lambda item: -targets[item]):

        if len(kept) >= edge_cap:
            break

        while degrees[node] < targets[node] and len(kept) < edge_cap:

            options = []

            for edge in candidates.values():

                if node not in (edge["u"], edge["v"]):
                    continue

                if (edge["u"], edge["v"]) in kept:
                    continue

                other = edge["v"] if edge["u"] == node else edge["u"]

                # Jangan sentuh node yang ditiator sebagai ujung jalan.
                if targets[other] <= 1 and degrees[other] >= 1:
                    continue

                if degrees[other] < targets[other] + 1:
                    options.append(edge)

            if not options:
                break

            edge = min(options, key=key)

            kept[(edge["u"], edge["v"])] = edge

            degrees[edge["u"]] += 1
            degrees[edge["v"]] += 1

    if len(_degrees(kept)) < len(targets):
        raise ValueError(
            "Pemilihan edge tidak menghasilkan graf terhubung."
        )

    return list(kept.values()), len(candidates), targets


def prune_edges(
    graph,
    distance,
    target_edges=TARGET_EDGES,
    min_degree=MIN_DEGREE,
    max_degree=MAX_DEGREE,
):
    """Memangkas edge berlebih tanpa memutus konektivitas graf."""

    candidates = unique_edges(graph, distance)

    kept = _minimum_spanning_tree(candidates)

    node_count = {edge["u"] for edge in candidates.values()}
    node_count.update(edge["v"] for edge in candidates.values())

    if len(_degrees(kept)) < len(node_count):
        raise ValueError(
            "Graf mentah tidak terhubung, pemangkasan edge tidak aman."
        )

    degrees = _degrees(kept)

    pool = [
        edge
        for key, edge in sorted(
            candidates.items(),
            key=lambda item: item[1]["cost"]
        )
        if key not in kept
    ]

    def attach(edge):

        kept[(edge["u"], edge["v"])] = edge

        degrees[edge["u"]] += 1
        degrees[edge["v"]] += 1

        pool.remove(edge)

    for _ in range(len(candidates)):

        under = {node for node, value in degrees.items() if value < min_degree}

        if not under:
            break

        options = [
            edge
            for edge in pool
            if (edge["u"] in under or edge["v"] in under)
            and degrees[edge["u"]] < max_degree
            and degrees[edge["v"]] < max_degree
        ]

        if not options:
            break

        attach(min(options, key=lambda edge: edge["cost"]))

    for _ in range(len(candidates) * 2):

        if len(kept) >= target_edges:
            break

        options = [
            edge
            for edge in pool
            if degrees[edge["u"]] < max_degree
            and degrees[edge["v"]] < max_degree
        ]

        if not options:
            break

        attach(min(options, key=lambda edge: edge["cost"]))

    return list(kept.values()), len(candidates)


def _edge_indices(edges, nodes):
    """Mengubah daftar edge menjadi indeks node."""

    index = {node: position for position, node in enumerate(nodes)}

    return [(index[edge["u"]], index[edge["v"]]) for edge in edges]


def initial_layout(
    edges,
    nodes,
    seed=LAYOUT_SEED,
    iterations=LAYOUT_ITERATIONS,
):
    """Menyebar node memakai gaya repulsif dan pegas pada setiap edge."""

    randomizer = random.Random(seed)

    total = len(nodes)

    margin = 2.0

    positions = []

    attempts = 0

    while len(positions) < total and attempts < 4000:

        attempts += 1

        point = (
            randomizer.uniform(margin, CANVAS_WIDTH - margin),
            randomizer.uniform(margin, CANVAS_HEIGHT - margin),
        )

        if all(
            math.dist(point, other) > MIN_SEPARATION * 0.7
            for other in positions
        ):
            positions.append(list(point))

    while len(positions) < total:

        positions.append([
            randomizer.uniform(margin, CANVAS_WIDTH - margin),
            randomizer.uniform(margin, CANVAS_HEIGHT - margin),
        ])

    home = [[CANVAS_WIDTH / 2, CANVAS_HEIGHT / 2] for _ in range(total)]

    links = _edge_indices(edges, nodes)

    ideal = (CANVAS_WIDTH * CANVAS_HEIGHT / max(len(edges), 1)) ** 0.5

    contact = MIN_SEPARATION * 1.2

    for step in range(iterations):

        push = [[0.0, 0.0] for _ in range(total)]

        for first in range(total):

            for second in range(first + 1, total):

                delta_x = positions[second][0] - positions[first][0]
                delta_y = positions[second][1] - positions[first][1]

                distance = math.hypot(delta_x, delta_y) or 1e-6

                force = 0.5 * contact * contact / distance

                if distance < contact:
                    force = max(force, (contact - distance) * 4.0)

                unit_x = delta_x / distance
                unit_y = delta_y / distance

                push[first][0] -= unit_x * force
                push[first][1] -= unit_y * force

                push[second][0] += unit_x * force
                push[second][1] += unit_y * force

        for first, second in links:

            delta_x = positions[second][0] - positions[first][0]
            delta_y = positions[second][1] - positions[first][1]

            distance = math.hypot(delta_x, delta_y) or 1e-6

            force = (distance - ideal) * 0.22

            unit_x = delta_x / distance * force
            unit_y = delta_y / distance * force

            push[first][0] += unit_x
            push[first][1] += unit_y

            push[second][0] -= unit_x
            push[second][1] -= unit_y

        damping = 0.10 * (1.0 - 0.5 * step / iterations)

        for position in range(total):

            push[position][0] += (home[position][0] - positions[position][0]) * 0.006
            push[position][1] += (home[position][1] - positions[position][1]) * 0.006

            positions[position][0] = min(
                max(positions[position][0] + push[position][0] * damping, 0.0),
                CANVAS_WIDTH
            )

            positions[position][1] = min(
                max(positions[position][1] + push[position][1] * damping, 0.0),
                CANVAS_HEIGHT
            )

    return positions


def _orientation(first, second, third):
    """Menghitung nilai determinan arah tiga titik."""

    return (
        (second[0] - first[0]) * (third[1] - first[1])
        - (second[1] - first[1]) * (third[0] - first[0])
    )


def _opposite(first, second, epsilon=1e-9):
    """Memeriksa apakah dua determinan berlawanan tanda."""

    return (
        (first > epsilon and second < -epsilon)
        or (first < -epsilon and second > epsilon)
    )


def segments_cross(first_start, first_end, second_start, second_end):
    """Mendeteksi perpotongan tegak lurus di tengah kedua ruas."""

    return (
        _opposite(
            _orientation(second_start, second_end, first_start),
            _orientation(second_start, second_end, first_end)
        )
        and _opposite(
            _orientation(first_start, first_end, second_start),
            _orientation(first_start, first_end, second_end)
        )
    )


def segment_intersection(first_start, first_end, second_start, second_end):
    """Mengembalikan parameter t dan u titik potong, atau None."""

    direction_x = first_end[0] - first_start[0]
    direction_y = first_end[1] - first_start[1]

    other_x = second_end[0] - second_start[0]
    other_y = second_end[1] - second_start[1]

    denominator = direction_x * other_y - direction_y * other_x

    if abs(denominator) < 1e-12:
        return None

    offset_x = second_start[0] - first_start[0]
    offset_y = second_start[1] - first_start[1]

    t = (offset_x * other_y - offset_y * other_x) / denominator

    u = (offset_x * direction_y - offset_y * direction_x) / denominator

    if not 0.0 < t < 1.0 or not 0.0 < u < 1.0:
        return None

    return t, u


def crossing_candidates(edges):
    """Menyiapkan pasangan edge yang tidak berbagi endpoint."""

    pairs = []

    for position, first in enumerate(edges):

        for second in edges[position + 1:]:

            if len({first[0], first[1], second[0], second[1]}) < 4:
                continue

            pairs.append((
                (first[0], first[1]),
                (second[0], second[1])
            ))

    return pairs


def count_crossings(positions, candidates):
    """Menghitung jumlah perpotongan edge."""

    total = 0

    for (first_a, first_b), (second_a, second_b) in candidates:

        if segments_cross(
            positions[first_a],
            positions[first_b],
            positions[second_a],
            positions[second_b]
        ):
            total += 1

    return total


def _spacing_penalty(positions, node_pairs, min_separation):
    """Menghitung penalti node yang masih terlalu berdekatan."""

    penalty = 0.0

    for first, second in node_pairs:

        gap = min_separation - math.dist(positions[first], positions[second])

        if gap > 0:
            penalty += gap * gap

    return penalty


def count_crossings_indexed(positions, candidates):
    """Menghitung perpotongan pada daftar koordinat berindeks."""

    total = 0

    for (first_a, first_b), (second_a, second_b) in candidates:

        if segments_cross(
            positions[first_a],
            positions[first_b],
            positions[second_a],
            positions[second_b]
        ):
            total += 1

    return total


def point_segment_distance(point, start, end):
    """Jarak titik ke ruas garis."""

    delta_x = end[0] - start[0]
    delta_y = end[1] - start[1]

    length = delta_x * delta_x + delta_y * delta_y

    if length < 1e-12:
        return math.dist(point, start)

    t = ((point[0] - start[0]) * delta_x + (point[1] - start[1]) * delta_y) / length

    t = max(0.0, min(1.0, t))

    return math.hypot(
        point[0] - (start[0] + delta_x * t),
        point[1] - (start[1] + delta_y * t)
    )


def point_segment_distances_pairs(points, starts, ends):
    """Jarak titik ke ruas secara pairwise, dihitung vektorisasi dengan numpy.

    Elemen ke-i pada ``points`` diukur terhadap ruas ke-i pada
    ``starts``/``ends``, sehingga kompleksitasnya linear.
    """

    import numpy

    points = numpy.asarray(points, dtype=float)
    starts = numpy.asarray(starts, dtype=float)
    ends = numpy.asarray(ends, dtype=float)

    delta = ends - starts

    length = (delta * delta).sum(axis=-1)

    safe = numpy.where(length < 1e-12, 1.0, length)

    offset = points - starts

    t = (offset * delta).sum(axis=-1) / safe

    t = numpy.clip(t, 0.0, 1.0)

    gap = points - (starts + delta * t[:, None])

    return numpy.sqrt((gap * gap).sum(axis=-1))


def _geometry_penalty(positions, node_edge_pairs, edge_pairs):
    """Penalti untuk geometri ambigu: node di atas ruas dan ruas tumpang tindih.

    Kedua kondisi ini tidak tertangkap uji perpotongan tegak lurus, padahal
    keduanya tampil sebagai "jalan bercabang tanpa persimpangan" di peta.
    """

    if not node_edge_pairs and not edge_pairs:
        return 0.0

    import numpy

    points = numpy.asarray(positions, dtype=float)

    penalty = 0.0

    if node_edge_pairs:

        nodes = numpy.asarray(
            [pair[0] for pair in node_edge_pairs], dtype=int
        )

        starts = numpy.asarray(
            [positions[pair[1][0]] for pair in node_edge_pairs], dtype=float
        )

        ends = numpy.asarray(
            [positions[pair[1][1]] for pair in node_edge_pairs], dtype=float
        )

        gaps = numpy.clip(
            ON_EDGE_CLEARANCE - point_segment_distances_pairs(
                points[nodes], starts, ends
            ),
            0.0,
            None
        )

        penalty += float((gaps * gaps).sum()) * ON_EDGE_WEIGHT

    if edge_pairs:

        first_a = numpy.asarray(
            [positions[pair[0][0]] for pair in edge_pairs], dtype=float
        )

        first_b = numpy.asarray(
            [positions[pair[0][1]] for pair in edge_pairs], dtype=float
        )

        second_a = numpy.asarray(
            [positions[pair[1][0]] for pair in edge_pairs], dtype=float
        )

        second_b = numpy.asarray(
            [positions[pair[1][1]] for pair in edge_pairs], dtype=float
        )

        closest = numpy.minimum(
            numpy.minimum(
                point_segment_distances_pairs(first_a, second_a, second_b),
                point_segment_distances_pairs(first_b, second_a, second_b)
            ),
            numpy.minimum(
                point_segment_distances_pairs(second_a, first_a, first_b),
                point_segment_distances_pairs(second_b, first_a, first_b)
            )
        )

        gaps = numpy.clip(CLEARANCE - closest, 0.0, None)

        penalty += float((gaps * gaps).sum()) * CLEARANCE_WEIGHT

    return penalty


def crossing_index_candidates(edges, nodes):
    """Pasangan edge yang tidak berbagi endpoint dalam bentuk indeks node."""

    index = {node: position for position, node in enumerate(nodes)}

    pairs = []

    for position, first in enumerate(edges):

        for second in edges[position + 1:]:

            if len({first[0], first[1], second[0], second[1]}) < 4:
                continue

            pairs.append((
                (index[first[0]], index[first[1]]),
                (index[second[0]], index[second[1]]),
            ))

    return pairs


def _layout_cost(positions, candidates, node_pairs, node_edge_pairs, edge_pairs):
    """Menggabungkan penalti perpotongan, jarak node, dan kejelasan geometri.

    ``positions`` adalah daftar koordinat sesuai urutan ``nodes`` sehingga
    perhitungan tetap cepat tanpa membangun dict pada tiap evaluasi.
    """

    crossings = 0

    for (first_a, first_b), (second_a, second_b) in candidates:

        if segments_cross(
            positions[first_a],
            positions[first_b],
            positions[second_a],
            positions[second_b]
        ):
            crossings += 1

    return (
        CROSSING_WEIGHT * crossings
        + _spacing_penalty(positions, node_pairs, MIN_SEPARATION)
        + _geometry_penalty(positions, node_edge_pairs, edge_pairs)
    )


def anneal_layout(positions, candidates, node_pairs, node_edge_pairs, edge_pairs, order, seed=LAYOUT_SEED):
    """Menekan perpotongan dan kondisi geometri ambigu dengan simulated annealing."""

    randomizer = random.Random(seed)

    best = _layout_cost(positions, candidates, node_pairs, node_edge_pairs, edge_pairs)

    best_positions = [list(point) for point in positions]

    current = best

    sweeps = ANNEAL_SWEEPS

    for sweep in range(sweeps):

        temperature = 10.0 * (0.05 / 10.0) ** (sweep / sweeps)

        for node in order:

            current_point = positions[node][:]

            angle = randomizer.uniform(0, 2 * math.pi)

            length = randomizer.uniform(0.8, 5.0)

            positions[node] = [
                min(max(current_point[0] + math.cos(angle) * length, 0.0),
                    CANVAS_WIDTH),
                min(max(current_point[1] + math.sin(angle) * length, 0.0),
                    CANVAS_HEIGHT),
            ]

            candidate = _layout_cost(
                positions, candidates, node_pairs, node_edge_pairs, edge_pairs
            )

            accept = candidate < current or randomizer.random() < math.exp(
                -(candidate - current) / max(temperature, 1e-9)
            )

            if accept:

                current = candidate

                if candidate < best:
                    best = candidate
                    best_positions = [list(point) for point in positions]

            else:
                positions[node] = current_point

    return best_positions


def _informed_moves(positions, node, neighbours, limit=6):
    """Kposisi kandidat yang lebih terarah: berat tetangganya sendiri.

    Lompatan acak sering meleset. Memindahkan node ke titik berat tetangganya,
    atau ke titik tengah dua tetangga yang paling dekat, jauh lebih sering
    langsung menekan perpotongan daripada bergerak acak buta.
    """

    if not neighbours:
        return []

    points = [positions[other] for other in neighbours]

    centre_x = sum(point[0] for point in points) / len(points)
    centre_y = sum(point[1] for point in points) / len(points)

    moves = [(centre_x, centre_y)]

    pairs = []

    for first, second in itertools.combinations(neighbours, 2):

        pairs.append((
            math.dist(positions[first], positions[second]),
            first, second
        ))

    for _gap, first, second in sorted(pairs)[:limit]:

        a = positions[first]
        b = positions[second]

        moves.append(((a[0] + b[0]) / 2, (a[1] + b[1]) / 2))

    return moves


def stabilize_layout(positions, candidates, node_pairs, node_edge_pairs, edge_pairs, order, links=None, max_passes=14):
    """Penyempurnaan akhir dengan pencarian arah yang deterministik."""

    best = _layout_cost(positions, candidates, node_pairs, node_edge_pairs, edge_pairs)

    step = 3.0

    passes = 0

    while step > 1e-3 and passes < max_passes:

        improved = False

        passes += 1

    for node in order:

        current_point = positions[node][:]

        for offset_x, offset_y in DIRECTIONS:

            positions[node] = [
                min(max(current_point[0] + offset_x * step, 0.0), CANVAS_WIDTH),
                min(max(current_point[1] + offset_y * step, 0.0), CANVAS_HEIGHT),
            ]

            if positions[node] == current_point:
                continue

            candidate = _layout_cost(
                positions, candidates, node_pairs, node_edge_pairs, edge_pairs
            )

            if candidate < best - 1e-9:
                best = candidate
                current_point = positions[node][:]
                improved = True
            else:
                positions[node] = current_point

        if links is None or step < 0.4:
            continue

        for move_x, move_y in _informed_moves(positions, node, links[node]):

            positions[node] = [
                min(max(move_x, 0.0), CANVAS_WIDTH),
                min(max(move_y, 0.0), CANVAS_HEIGHT)
            ]

            if positions[node] == current_point:
                continue

            candidate = _layout_cost(
                positions, candidates, node_pairs, node_edge_pairs, edge_pairs
            )

            if candidate < best - 1e-9:
                best = candidate
                current_point = positions[node][:]
                improved = True
            else:
                positions[node] = current_point

    if not improved:
        step *= 0.5

    return positions


def polish_crossings(positions, candidates, order, steps=(2.0, 1.0, 0.5, 0.25, 0.1)):
    """Menghapus perpotongan sisa dengan ê¹ƒ kecil khusus tabrakan.

    Tahap ini mengabaikan penalti jarak dan hanya mengejar penurunan jumlah
    perpotongan, sehingga perpotongan yang tersisa di dekat sebuah node tetap
    dapat dihilangkan tanpa menggeser tata letak secara signifikan.
    """

    best = count_crossings_indexed(positions, candidates)

    for step in steps:

        improved = True

        while improved:

            improved = False

            for node in order:

                current_point = positions[node][:]

                for offset_x, offset_y in DIRECTIONS:

                    positions[node] = [
                        min(max(current_point[0] + offset_x * step, 0.0), CANVAS_WIDTH),
                        min(max(current_point[1] + offset_y * step, 0.0), CANVAS_HEIGHT),
                    ]

                    if positions[node] == current_point:
                        continue

                    candidate = count_crossings_indexed(positions, candidates)

                    if candidate < best:
                        best = candidate
                        current_point = positions[node][:]
                        improved = True
                    else:
                        positions[node] = current_point

    return positions, best


def arrange_coordinates(edges):
    """Menyusun koordinat baru yang berjauhan dan minim perpotongan."""

    nodes = list(SOURCE_COORDINATES)

    edge_list = [(edge["u"], edge["v"]) for edge in edges]

    name_candidates = crossing_candidates(edge_list)

    candidates = crossing_index_candidates(edge_list, nodes)

    node_pairs = [
        (first, second)
        for first in range(len(nodes))
        for second in range(first + 1, len(nodes))
    ]

    edge_pairs = candidates

    index_links = _edge_indices(edges, nodes)

    neighbour_index = defaultdict(set)

    for first, second in index_links:
        neighbour_index[first].add(second)
        neighbour_index[second].add(first)

    links = [sorted(neighbour_index[node]) for node in range(len(nodes))]

    node_edge_pairs = [
        (node, link)
        for node in range(len(nodes))
        for link in index_links
        if node not in link
    ]

    degree = defaultdict(int)

    for first, second in edge_list:
        degree[first] += 1
        degree[second] += 1

    order = sorted(range(len(nodes)), key=lambda node: -degree[nodes[node]])

    before = count_crossings(
        {node: initial_layout(edges, nodes, seed=LAYOUT_SEEDS[0])[position]
         for position, node in enumerate(nodes)},
        name_candidates
    )

    best_positions = None

    best_score = None

    for seed in LAYOUT_SEEDS:

        positions = initial_layout(edges, nodes, seed=seed)

        positions = anneal_layout(
            positions, candidates, node_pairs, node_edge_pairs, edge_pairs,
            order, seed=seed
        )

        positions = stabilize_layout(
            positions, candidates, node_pairs, node_edge_pairs, edge_pairs,
            order, links
        )

        positions, _remaining = polish_crossings(positions, candidates, order)

        score = _layout_cost(
            positions, candidates, node_pairs, node_edge_pairs, edge_pairs
        )

        crossings = count_crossings_indexed(positions, candidates)

        print(
            f"  seed {seed}: perpotongan {crossings} Â· "
            f"biaya tata letak {score:.2f}"
        )

        if best_score is None or score < best_score:

            best_score = score
            best_positions = [list(point) for point in positions]

    positions = best_positions

    coordinates = {
        node: (round(positions[position][0], 2), round(positions[position][1], 2))
        for position, node in enumerate(nodes)
    }

    return coordinates, before, count_crossings(coordinates, name_candidates)


def _register_junction(point, positions, junctions, grid, index, tolerance):
    """Mendaftarkan titik potong sebagai node persimpangan.

    Bila titik potong berada sangat dekat sebuah node yang sudah ada, titik itu
    langsung memakai node tersebut. Hal ini menafsirkan jalan yang melintas tepat
    pada sebuah persimpangan sebagai jalan yang benar-benar tersambung ke
    persimpangan itu, bukan sebagai persimpangan baru yang bertumpuk.
    """

    nearest = None

    nearest_distance = tolerance

    for node, location in positions.items():

        distance = math.dist(point, location)

        if distance < nearest_distance:
            nearest_distance = distance
            nearest = node

    if nearest is not None:
        return nearest, False

    cell = (int(point[0] // tolerance), int(point[1] // tolerance))

    for offset_x in (-1, 0, 1):

        for offset_y in (-1, 0, 1):

            neighbour = (cell[0] + offset_x, cell[1] + offset_y)

            for key in grid.get(neighbour, ()):

                if math.dist(point, junctions[key]["position"]) <= tolerance:
                    return key, False

    name = label_from_index(index)

    junctions[name] = {"position": (point[0], point[1])}

    grid.setdefault(cell, []).append(name)

    return name, True


def create_junction_nodes(coordinates, edges, tolerance=JUNCTION_TOLERANCE):
    """Menjadikan setiap titik potong edge sebagai node yang dapat dilalui."""

    positions = dict(coordinates)

    nodes = list(positions)

    times = {node: {} for node in nodes}

    distances = {node: {} for node in nodes}

    edge_list = []

    for edge in edges:

        first, second = edge["u"], edge["v"]

        edge_list.append((first, second))

        times[first][second] = edge["time"]
        times[second][first] = edge["time"]

        distances[first][second] = edge["distance"]
        distances[second][first] = edge["distance"]

    junctions = {}

    grid = {}

    index = max(label_index(node) for node in nodes) + 1

    splits = defaultdict(list)

    for position, (first_a, first_b) in enumerate(edge_list):

        point_a = positions[first_a]
        point_b = positions[first_b]

        for second_a, second_b in edge_list[position + 1:]:

            if len({first_a, first_b, second_a, second_b}) < 4:
                continue

            hit = segment_intersection(
                point_a,
                point_b,
                positions[second_a],
                positions[second_b]
            )

            if hit is None:
                continue

            t, u = hit

            if not MIN_SPLIT_FRACTION < t < 1.0 - MIN_SPLIT_FRACTION:
                continue

            if not MIN_SPLIT_FRACTION < u < 1.0 - MIN_SPLIT_FRACTION:
                continue

            meeting = (
                point_a[0] + (point_b[0] - point_a[0]) * t,
                point_a[1] + (point_b[1] - point_a[1]) * t,
            )

            key, created = _register_junction(
                meeting, positions, junctions, grid, index, tolerance
            )

            if created:
                index += 1

            splits[(first_a, first_b)].append((t, key))
            splits[(second_a, second_b)].append((u, key))

    for first, second in edge_list:

        for node in nodes:

            if node == first or node == second:
                continue

            if node not in positions:
                continue

            gap = point_segment_distance(
                positions[node], positions[first], positions[second]
            )

            if gap > ON_EDGE_TOLERANCE:
                continue

            direction_x = positions[second][0] - positions[first][0]
            direction_y = positions[second][1] - positions[first][1]

            span = direction_x * direction_x + direction_y * direction_y

            if span < 1e-12:
                continue

            t = (
                (positions[node][0] - positions[first][0]) * direction_x
                + (positions[node][1] - positions[first][1]) * direction_y
            ) / span

            if not MIN_SPLIT_FRACTION < t < 1.0 - MIN_SPLIT_FRACTION:
                continue

            splits[(first, second)].append((t, node))

    for key, value in junctions.items():

        positions[key] = (
            round(value["position"][0], 2),
            round(value["position"][1], 2)
        )

    raw_times = {}

    raw_distances = {}

    final_times = {node: {} for node in positions}

    final_distances = {node: {} for node in positions}

    def link(first, second, minutes, kilometers):

        key = (first, second) if first <= second else (second, first)

        previous = raw_times.get(key)

        if previous is not None:
            minutes = max(previous, minutes)
            kilometers = max(raw_distances[key], kilometers)

        raw_times[key] = minutes

        raw_distances[key] = kilometers

    for first, second in edge_list:

        marks = sorted(splits.get((first, second), []))

        if not marks:

            link(first, second, times[first][second], distances[first][second])

            continue

        chain = [first] + [key for _value, key in marks] + [second]

        shares = [0.0] + [value for value, _key in marks] + [1.0]

        for position in range(len(chain) - 1):

            start = chain[position]
            end = chain[position + 1]

            share = shares[position + 1] - shares[position]

            if start == end or share <= 1e-9:
                continue

            minutes = max(1, int(round(times[first][second] * share)))

            kilometers = max(
                0.1,
                round(distances[first][second] * share, 1)
            )

            link(start, end, minutes, kilometers)

    for key, minutes in raw_times.items():

        final_times[key[0]][key[1]] = minutes
        final_times[key[1]][key[0]] = minutes

    for key, kilometers in raw_distances.items():

        final_distances[key[0]][key[1]] = kilometers
        final_distances[key[1]][key[0]] = kilometers

    return positions, final_times, final_distances, sorted(junctions)


def build_graph():
    """Menjalankan seluruh tahapan dan mengembalikan graf siap pakai."""

    edges, original_count, targets = select_edges(SOURCE_GRAPH, SOURCE_DISTANCE)

    coordinates, before, after = arrange_coordinates(edges)

    positions, graph, distance, junctions = create_junction_nodes(
        coordinates, edges
    )

    degrees = _degrees({(e["u"], e["v"]): e for e in edges})

    report = {
        "edge_mentah": original_count,
        "edge_dipilih": len(edges),
        "derajat_min": min(degrees.values()),
        "derajat_maks": max(degrees.values()),
        "derajat_rata": round(sum(degrees.values()) / len(degrees), 2),
        "titik_potong_sebelum": before,
        "titik_potong_sesudah": after,
        "node_persimpangan": len(junctions),
        "node_total": len(positions),
        "edge_total": sum(len(row) for row in graph.values()) // 2,
    }

    return positions, graph, distance, tuple(junctions), report


def _format_node_table(coordinates, indent="    "):
    """Menyusun blok dict koordinat."""

    lines = ["{"]

    for node, (x, y) in coordinates.items():

        value = f"({x:g}, {y:g})"

        lines.append(f'{indent}"{node}": {value},')

    lines.append("}")

    return "\n".join(lines)


def _format_edge_table(table, indent="    "):
    """Menyusun blok dict edge (waktu atau jarak)."""

    lines = ["{"]

    for node in sorted(table):

        row = table[node]

        if not row:
            lines.append(f'{indent}"{node}": {{}},')
            continue

        cells = ",".join(
            f'"{neighbor}":{row[neighbor]:g}' for neighbor in sorted(row)
        )

        lines.append(f'{indent}"{node}": {{{cells}}},')

    lines.append("}")

    return "\n".join(lines)


def render_data_module(coordinates, graph, distance, junctions):
    """Menyusun isi modul data.py lengkap dengan database kendaraan."""

    current = DATA_MODULE.read_text(encoding="utf-8")

    if DATABASE_MARKER not in current:
        raise ValueError(
            f"Penanda {DATABASE_MARKER} tidak ditemukan pada {DATA_MODULE}."
        )

    databases = current[current.index(DATABASE_MARKER):]

    junction_names = ", ".join(f'"{name}"' for name in junctions)

    return (
        '"""Data graf, kendaraan, bahan bakar, dan paket layanan.\n'
        "\n"
        "Blok COORDINATES, GRAPH, dan DISTANCE di bawah dihasilkan oleh\n"
        "`python -m pka_route.graph_builder` dari data mentah A-Z yang disimpan\n"
        "pada pka_route/graph_builder.py. Node AA dan seterusnya adalah titik\n"
        "persimpangan yang dapat dilalui.\n"
        '"""\n'
        "\n"
        f"COORDINATES = {_format_node_table(coordinates)}\n"
        "\n"
        f"GRAPH = {_format_edge_table(graph)}\n"
        "\n"
        f"DISTANCE = {_format_edge_table(distance)}\n"
        "\n"
        "JUNCTION_NODES = frozenset({"
        f"{junction_names}"
        "})\n"
        "\n"
        f"{databases}"
    )


def main():
    """Menulis ulang pka_route/data.py dari data mentah."""

    coordinates, graph, distance, junctions, report = build_graph()

    DATA_MODULE.write_text(
        render_data_module(coordinates, graph, distance, junctions),
        encoding="utf-8"
    )

    print("pka_route/data.py berhasil ditulis ulang:")

    for key, value in report.items():
        print(f"  {key}: {value}")

    print(f"  persimpangan: {', '.join(junctions) or '(tidak ada)'}")

    return report


if __name__ == "__main__":
    main()
