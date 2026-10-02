"""Visualisasi graf rute: peta jaringan, panel zoom, dan fokus rute optimal."""

import csv
import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt

from matplotlib.cm import ScalarMappable

from matplotlib.colors import Normalize

from matplotlib.patheffects import withStroke

from matplotlib.ticker import MultipleLocator

from .data import COORDINATES, DISTANCE, GRAPH, JUNCTION_NODES

from .metrics import calculate_fuel_cost


BASE_DIR = Path(__file__).resolve().parent.parent

OUTPUT_DIR = BASE_DIR / "output"

EXPERIMENT_CSV = OUTPUT_DIR / "eksperimen.csv"

NODE_FILL = "#ffffff"

NODE_EDGE = "#1f3a5f"

NODE_TEXT = "#1f3a5f"

START_COLOR = "#1b8a5a"

GOAL_COLOR = "#c92a2a"

ROUTE_COLOR = "#e8590c"

JUNCTION_COLOR = "#f08c00"

EDGE_COLORMAP = "viridis"

HEADER_IN = 0.95

FOOTER_IN = 0.62

PAD_IN = 0.55

TICK_STEPS = (1, 2, 5, 10, 20, 50, 100)

MAP_PADDING_RATIO = 0.05

LOCATION_NODES = [
    node for node in COORDINATES
    if node not in JUNCTION_NODES
]


def map_limits(padding_ratio=MAP_PADDING_RATIO):
    """Menghitung batas tampilan langsung dari koordinat node."""

    xs = [point[0] for point in COORDINATES.values()]

    ys = [point[1] for point in COORDINATES.values()]

    pad_x = (max(xs) - min(xs)) * padding_ratio or 4.0

    pad_y = (max(ys) - min(ys)) * padding_ratio or 4.0

    return (min(xs) - pad_x, max(xs) + pad_x, min(ys) - pad_y, max(ys) + pad_y)


def route_limits(route, padding_ratio=0.22):
    """Menghitung batas tampilan yang membingkai node pada rute."""

    nodes = [node for node in route if node in COORDINATES]

    if not nodes:
        return map_limits()

    xs = [COORDINATES[node][0] for node in nodes]

    ys = [COORDINATES[node][1] for node in nodes]

    pad_x = (max(xs) - min(xs)) * padding_ratio or 8.0

    pad_y = (max(ys) - min(ys)) * padding_ratio or 8.0

    return (min(xs) - pad_x, max(xs) + pad_x, min(ys) - pad_y, max(ys) + pad_y)


def build_panel_specs(route=None):
    """Menyusun panel zoom dari batas peta hasil perhitungan."""

    x0, x1, y0, y1 = map_limits()

    mid_x = (x0 + x1) / 2

    mid_y = (y0 + y1) / 2

    specs = [
        ("Peta Lengkap", "seluruh jaringan", (x0, x1), (y0, y1)),
        ("Panel 1 - Barat Laut", "kuartir kiri atas", (x0, mid_x), (mid_y, y1)),
        ("Panel 2 - Timur Laut", "kuartir kanan atas", (mid_x, x1), (mid_y, y1)),
        ("Panel 3 - Barat Daya", "kuartir kiri bawah", (x0, mid_x), (y0, mid_y)),
        ("Panel 4 - Timur Daya", "kuartir kanan bawah", (mid_x, x1), (y0, mid_y)),
    ]

    if route and len(route) > 1:

        specs.append((
            "Panel 5 - Rute Optimal",
            "wilayah yang dilalui rute",
            route_limits(route)[:2],
            route_limits(route)[2:]
        ))

    return specs


def read_experiment(path=EXPERIMENT_CSV):
    """Membaca baris eksperimen terakhir sebagai konfigurasi aktif."""

    if not path.exists():

        return None

    with path.open(newline="", encoding="utf-8") as handle:

        rows = list(csv.DictReader(handle))

    if not rows:

        return None

    return rows[-1]


def undirected_edges():
    """Menghasilkan daftar edge unik (graf bersifat tak berarah)."""

    edges = {}

    for node, neighbors in GRAPH.items():

        for neighbor in neighbors:

            key = tuple(sorted((node, neighbor)))

            if key in edges:

                continue

            if neighbor in GRAPH[node]:

                travel_time = float(GRAPH[node][neighbor])
                distance = float(DISTANCE[node][neighbor])

            else:

                travel_time = float(GRAPH[neighbor][node])
                distance = float(DISTANCE[neighbor][node])

            edges[key] = {
                "u": key[0],
                "v": key[1],
                "time": travel_time,
                "distance": distance,
            }

    return [edges[key] for key in sorted(edges)]


def node_degrees():
    """Menghitung derajat tiap node."""

    edges = undirected_edges()

    degrees = {node: 0 for node in GRAPH}

    for edge in edges:

        degrees[edge["u"]] += 1
        degrees[edge["v"]] += 1

    return degrees


def enrich_edges(fuel_price_km):
    """Menambahkan biaya bahan bakar ke tiap edge."""

    edges = undirected_edges()

    for edge in edges:

        edge["fuel"] = calculate_fuel_cost(
            edge["distance"],
            fuel_price_km
        )

    return edges


def edge_label(edge, style="compact"):
    """Menyusun teks informasi yang ditampilkan pada edge."""

    if style == "compact":

        return f"{edge['distance']:.1f} km · {edge['time']:.0f}′"

    if style == "full":

        fuel = f"Rp{edge['fuel']:,.0f}".replace(",", ".")

        return (
            f"{edge['distance']:.1f} km · {edge['time']:.0f}′\n"
            f"{fuel}"
        )

    if style == "tiny":

        return f"{edge['distance']:.1f} / {edge['time']:.0f}"

    return None


def _inside(x, y, xlim, ylim, margin=0.0):
    """Memeriksa apakah titik berada di dalam area panel."""

    return (
        xlim[0] - margin <= x <= xlim[1] + margin
        and ylim[0] - margin <= y <= ylim[1] + margin
    )


def _pick_step(span):
    """Memilih jarak tick yang enak dibaca."""

    for step in TICK_STEPS:

        if span / step <= 8:

            return step

    return TICK_STEPS[-1]


def _style_axes(ax, xlim, ylim):
    """Menyamakan rasio kotak sumbu dengan rasio data."""

    ax.set_xlim(*xlim)
    ax.set_ylim(*ylim)

    ax.set_aspect("equal", adjustable="box")

    x_step = _pick_step(xlim[1] - xlim[0])
    y_step = _pick_step(ylim[1] - ylim[0])

    ax.xaxis.set_major_locator(MultipleLocator(x_step))
    ax.yaxis.set_major_locator(MultipleLocator(y_step))

    ax.tick_params(labelsize=7, colors="#5a6b7d")

    ax.set_facecolor("#fbfcfd")

    ax.grid(
        True,
        linestyle=":",
        linewidth=0.5,
        color="#c9d2dc",
        alpha=0.7
    )

    ax.set_axisbelow(True)

    for spine in ax.spines.values():

        spine.set_color("#c9d2dc")


def _make_canvas(ratio, map_width_in, right_extra_in=0.0):
    """Membuat kanvas dengan ukuran peta pas terhadap rasio data."""

    map_height_in = map_width_in / ratio

    figure_width = PAD_IN + map_width_in + right_extra_in + PAD_IN

    figure_height = (
        PAD_IN + HEADER_IN + map_height_in + FOOTER_IN
    )

    figure = plt.figure(figsize=(figure_width, figure_height))

    ax = figure.add_axes([
        PAD_IN / figure_width,
        (PAD_IN + FOOTER_IN) / figure_height,
        map_width_in / figure_width,
        map_height_in / figure_height,
    ])

    return figure, ax


def _add_header(figure, title, subtitle=None):
    """Menuliskan judul utama dan keterangan gambar."""

    figure.text(
        0.5,
        1.0 - (PAD_IN * 0.5) / figure.get_figheight(),
        title,
        ha="center",
        va="center",
        fontsize=14,
        fontweight="bold",
        color=NODE_EDGE
    )

    if subtitle:

        figure.text(
            0.5,
            1.0 - (PAD_IN * 0.5 + 0.32) / figure.get_figheight(),
            subtitle,
            ha="center",
            va="center",
            fontsize=8.5,
            color="#5a6b7d"
        )


def _add_footnote(figure, config, extra):
    """Menuliskan konfigurasi eksperimen di bawah gambar."""

    if config:

        detail = (
            f"{config['vehicle_name']} ({config['km_per_liter']} km/L) · "
            f"{config['fuel_name']} "
            f"(Rp{config['fuel_price_per_liter']}/L) · "
            f"{config['service_name']} "
            f"[J_W={config['distance_weight']}, W_W={config['time_weight']}]"
        )

    else:

        detail = "Konfigurasi eksperimen tidak ditemukan"

    figure.text(
        0.5,
        (PAD_IN * 0.45) / figure.get_figheight(),
        f"{extra}   |   {detail}",
        ha="center",
        va="center",
        fontsize=8,
        color="#5a6b7d"
    )


def _node_marker_size(diameter, span, axes_width_in):
    """Mengubah diameter node (satuan data) menjadi ukuran marker."""

    points = diameter / span * axes_width_in * 72.0

    return max(60.0, min(points ** 2, 4000.0))


def _place_edge_label(
    ax,
    edge,
    text,
    size,
    alpha,
    offset,
    clip=True
):
    """Menempatkan label edge di tengah dengan offset tegak lurus."""

    (x1, y1) = COORDINATES[edge["u"]]
    (x2, y2) = COORDINATES[edge["v"]]

    delta_x = x2 - x1
    delta_y = y2 - y1

    length = math.hypot(delta_x, delta_y) or 1.0

    mid_x = (x1 + x2) / 2 - delta_y / length * offset
    mid_y = (y1 + y2) / 2 + delta_x / length * offset

    return ax.text(
        mid_x,
        mid_y,
        text,
        ha="center",
        va="center",
        fontsize=size,
        color="#16222e",
        alpha=alpha,
        zorder=3,
        linespacing=1.0,
        clip_on=clip,
        path_effects=[
            withStroke(linewidth=2.0, foreground="white", alpha=0.9)
        ],
    )


def draw_network(
    ax,
    edges,
    degrees,
    start,
    goal,
    route_pairs,
    xlim,
    ylim,
    axes_width_in,
    label_style="compact",
    label_size=6.0,
    label_alpha=0.95,
    node_diameter=1.3,
    edge_alpha=0.9,
    edge_width_scale=1.0,
    label_route_edges=True,
):
    """Menggambar jaringan jalan beserta informasi pada setiap edge."""

    if not edges:

        return [], plt.get_cmap(EDGE_COLORMAP), Normalize(0, 1)

    times = [edge["time"] for edge in edges]

    max_distance = max(edge["distance"] for edge in edges) or 1.0

    y_span = ylim[1] - ylim[0]

    offset = 0.035 * y_span

    route_pairs = {
        tuple(sorted(pair))
        for pair in route_pairs
    }

    cmap = plt.get_cmap(EDGE_COLORMAP)

    norm = Normalize(vmin=min(times), vmax=max(times))

    labels = []

    for edge in edges:

        (x1, y1) = COORDINATES[edge["u"]]
        (x2, y2) = COORDINATES[edge["v"]]

        is_route = (
            tuple(sorted((edge["u"], edge["v"])))
            in route_pairs
        )

        ax.plot(
            [x1, x2],
            [y1, y2],
            color=(
                ROUTE_COLOR if is_route
                else cmap(norm(edge["time"]))
            ),
            linewidth=(
                3.0 * edge_width_scale if is_route
                else edge_width_scale * _edge_width(
                    edge["distance"],
                    max_distance
                )
            ),
            alpha=1.0 if is_route else edge_alpha,
            zorder=2 if is_route else 1,
            solid_capstyle="round",
        )

        text = edge_label(edge, label_style)

        if text is None:

            continue

        if is_route and not label_route_edges:

            continue

        label = _place_edge_label(
            ax,
            edge,
            text,
            label_size,
            label_alpha,
            offset
        )

        if not _inside(
            (x1 + x2) / 2,
            (y1 + y2) / 2,
            xlim,
            ylim
        ):

            label.set_visible(False)
            continue

        labels.append((label, edge["distance"]))

    marker_size = _node_marker_size(
        node_diameter,
        y_span,
        axes_width_in
    )

    for node, (x, y) in COORDINATES.items():

        if not _inside(x, y, xlim, ylim):

            continue

        is_start = node == start
        is_goal = node == goal
        is_junction = node in JUNCTION_NODES

        size = marker_size * (0.80 + 0.045 * degrees.get(node, 0))

        base_font = max(6.5, node_diameter * 5.6)

        font_size = base_font * (0.78 if len(node) > 1 else 1.0)

        if is_start or is_goal:

            size *= 1.30

        elif is_junction:

            size = max(size, (font_size * 2.0) ** 2)

        ax.scatter(
            [x],
            [y],
            s=size,
            marker="D" if is_junction else "o",
            facecolor=(
                START_COLOR if is_start
                else GOAL_COLOR if is_goal
                else JUNCTION_COLOR if is_junction
                else NODE_FILL
            ),
            edgecolor=NODE_EDGE,
            linewidth=1.5,
            zorder=4,
            clip_on=True
        )

        ax.text(
            x,
            y,
            node,
            ha="center",
            va="center",
            fontsize=font_size,
            fontweight="bold",
            color="#ffffff" if (is_start or is_goal) else NODE_TEXT,
            zorder=5,
            clip_on=True
        )

    labels.sort(key=lambda item: item[1])

    return labels, cmap, norm


def _edge_width(distance, max_distance, min_width=0.7, max_width=4.0):
    """Menebalkan edge yang jaraknya pendek (jalan utama)."""

    ratio = 1.0 - (distance / max_distance)

    return min_width + ratio * (max_width - min_width)


def resolve_label_collisions(figure, labels, pad=0.9):
    """Menyembunyikan label edge yang saling bertumpuk."""

    if not labels:

        return 0

    figure.canvas.draw()

    renderer = figure.canvas.get_renderer()

    kept = []

    hidden = 0

    for text, _priority in labels:

        if not text.get_visible():

            continue

        bbox = text.get_window_extent(
            renderer=renderer
        ).padded(pad)

        if any(bbox.overlaps(existing) for existing in kept):

            text.set_visible(False)
            hidden += 1

        else:

            kept.append(bbox)

    return hidden


def _add_colorbar(figure, ax, cmap, norm):
    """Menambahkan skala warna waktu tempuh."""

    mappable = ScalarMappable(norm=norm, cmap=cmap)

    mappable.set_array([])

    bar = figure.colorbar(
        mappable,
        ax=ax,
        fraction=0.03,
        pad=0.02
    )

    bar.set_label("Waktu tempuh (menit)", fontsize=8)

    bar.ax.tick_params(labelsize=7)


def build_overview(edges, degrees, start, goal, route_pairs, config, path):
    """Gambar 1: seluruh jaringan dalam satu kanvas."""

    x0, x1, y0, y1 = map_limits()

    xlim = (x0, x1)

    ylim = (y0, y1)

    figure, ax = _make_canvas(
        (xlim[1] - xlim[0]) / (ylim[1] - ylim[0]),
        map_width_in=13.5,
        right_extra_in=1.1
    )

    labels, cmap, norm = draw_network(
        ax,
        edges,
        degrees,
        start,
        goal,
        route_pairs,
        xlim,
        ylim,
        axes_width_in=13.5,
        label_style="tiny",
        label_size=5.4,
        label_alpha=0.95,
        node_diameter=1.3,
        edge_alpha=0.55,
        edge_width_scale=1.15
    )

    _style_axes(ax, xlim, ylim)

    figure.canvas.draw()

    resolve_label_collisions(figure, labels, pad=0.6)

    figure.canvas.draw()

    _add_colorbar(figure, ax, cmap, norm)

    _add_header(
        figure,
        f"Graf Rute Pengiriman {len(LOCATION_NODES)} Lokasi (A-Z)",
        "Warna edge = waktu tempuh · tebal edge = jarak · "
        "label edge = jarak km / waktu menit · "
        "hijau = start · merah = goal · oranye = rute optimal · "
        "berlian oranye = persimpangan"
    )

    _add_footnote(
        figure,
        config,
        f"{len(edges)} edge · {len(GRAPH)} node "
        f"({len(LOCATION_NODES)} lokasi + {len(JUNCTION_NODES)} persimpangan) · "
        f"start {start} → goal {goal}"
    )

    figure.savefig(path, dpi=200, facecolor="white")

    plt.close(figure)


def _panel_layout(figure_width_in, figure_height_in, specs, gap_in=0.62):
    """Menghitung posisi setiap panel sesuai rasio data masing-masing."""

    columns = 3
    rows = 2

    slot_width = (figure_width_in - 2 * PAD_IN - gap_in * 2) / columns

    slot_height = (
        figure_height_in
        - 2 * PAD_IN
        - HEADER_IN
        - FOOTER_IN
        - gap_in
    ) / rows

    rects = []

    for index, (_title, _note, xlim, ylim) in enumerate(specs):

        row = index // columns

        column = index % columns

        ratio = (xlim[1] - xlim[0]) / (ylim[1] - ylim[0])

        width = min(slot_width, slot_height * ratio)
        height = width / ratio

        origin_x = PAD_IN + column * (slot_width + gap_in)
        origin_y = (
            figure_height_in - PAD_IN - FOOTER_IN
            - (row + 1) * slot_height
            - row * gap_in
            + (slot_height - height) / 2
        )

        rects.append((
            [
                origin_x / figure_width_in
                + (slot_width - width) / 2 / figure_width_in,
                origin_y / figure_height_in,
                width / figure_width_in,
                height / figure_height_in
            ],
            ratio
        ))

    return rects

def build_panels(edges, degrees, start, goal, route_pairs, config, path, route):
    """Gambar 2: peta lengkap dan panel zoom agar label edge terbaca."""

    specs = build_panel_specs(route)

    figure_width_in = 19.0

    figure_height_in = 13.0

    figure = plt.figure(figsize=(figure_width_in, figure_height_in))

    rects = _panel_layout(figure_width_in, figure_height_in, specs)

    all_labels = []

    for (title, note, xlim, ylim), (rect, _ratio) in zip(specs, rects):

        ax = figure.add_axes(rect)

        axes_width_in = rect[2] * figure_width_in

        panel_edges, border_edges = _edges_inside(edges, xlim, ylim)

        draw_network(
            ax,
            border_edges,
            degrees,
            start,
            goal,
            route_pairs,
            xlim,
            ylim,
            axes_width_in=axes_width_in,
            label_style=None,
            node_diameter=0.75,
            edge_alpha=0.20,
            edge_width_scale=0.9
        )

        labels, _cmap, _norm = draw_network(
            ax,
            panel_edges,
            degrees,
            start,
            goal,
            route_pairs,
            xlim,
            ylim,
            axes_width_in=axes_width_in,
            label_style="full",
            label_size=6.2,
            label_alpha=1.0,
            node_diameter=0.75,
            edge_alpha=0.95,
            edge_width_scale=1.5
        )

        all_labels.extend(labels)

        _style_axes(ax, xlim, ylim)

        ax.set_title(
            f"{title}  ·  {len(panel_edges)} edge utuh  ·  {note}",
            fontsize=10,
            fontweight="bold",
            color=NODE_EDGE,
            pad=4
        )

    figure.canvas.draw()

    resolve_label_collisions(figure, all_labels, pad=0.8)

    _add_header(
        figure,
        "Detail Edge Graf Rute (jarak · waktu · biaya bahan bakar)",
        "Tiap label edge: jarak (km) · waktu (menit) / biaya bahan bakar "
        "berdasarkan kendaraan dan bensin pada eksperimen aktif"
    )

    _add_footnote(
        figure,
        config,
        "Label yang bertumpuk otomatis disembunyikan agar tetap terbaca"
    )

    figure.savefig(path, dpi=190, facecolor="white")

    plt.close(figure)


def _edges_inside(edges, xlim, ylim):
    """Memisahkan edge utuh dan edge yang hanya menyentuh panel."""

    inner = []

    crossing = []

    for edge in edges:

        (x1, y1) = COORDINATES[edge["u"]]
        (x2, y2) = COORDINATES[edge["v"]]

        first_inside = _inside(x1, y1, xlim, ylim)
        second_inside = _inside(x2, y2, xlim, ylim)

        if first_inside and second_inside:

            inner.append(edge)

        elif first_inside or second_inside:

            crossing.append(edge)

    return inner, crossing


def _route_segments(edges, route, fuel_price_km):
    """Menghitung rincian tiap segmen pada rute optimal."""

    index = {
        tuple(sorted((edge["u"], edge["v"]))): edge
        for edge in edges
    }

    segments = []

    cumulative = [0.0, 0.0, 0.0]

    for position in range(len(route) - 1):

        key = tuple(sorted((route[position], route[position + 1])))

        edge = index[key]

        distance, time, fuel = edge_metrics_safe(edge, fuel_price_km)

        cumulative = [
            cumulative[0] + distance,
            cumulative[1] + time,
            cumulative[2] + fuel
        ]

        segments.append({
            "from": route[position],
            "to": route[position + 1],
            "distance": distance,
            "time": time,
            "fuel": fuel,
            "cumulative": tuple(cumulative)
        })

    return segments


def edge_metrics_safe(edge, fuel_price_km):
    """Mengambil metrik edge lengkap dengan biaya bahan bakar."""

    return (
        edge["distance"],
        edge["time"],
        calculate_fuel_cost(edge["distance"], fuel_price_km)
    )


def _rupiah(value, decimals=0):
    """Format angka rupiah dengan pemisah ribuan."""

    return f"Rp{value:,.{decimals}f}".replace(",", ".")


def build_route_focus(
    edges,
    degrees,
    start,
    goal,
    route,
    config,
    path,
    fuel_price_km
):
    """Gambar 3: rincian tiap edge pada rute optimal."""

    segments = _route_segments(edges, route, fuel_price_km)

    route_pairs = {
        (segment["from"], segment["to"])
        for segment in segments
    }

    x0, x1, y0, y1 = map_limits()

    xlim = (x0, x1)

    ylim = (y0, y1)

    map_width_in = 11.0

    table_width_in = 5.4

    figure, ax = _make_canvas(
        (xlim[1] - xlim[0]) / (ylim[1] - ylim[0]),
        map_width_in=map_width_in,
        right_extra_in=table_width_in
    )

    draw_network(
        ax,
        edges,
        degrees,
        start,
        goal,
        route_pairs,
        xlim,
        ylim,
        axes_width_in=map_width_in,
        label_style=None,
        node_diameter=1.3,
        edge_alpha=0.22,
        edge_width_scale=1.0
    )

    _style_axes(ax, xlim, ylim)

    for number, segment in enumerate(segments, start=1):

        (x1, y1) = COORDINATES[segment["from"]]
        (x2, y2) = COORDINATES[segment["to"]]

        ax.annotate(
            "",
            xy=(x2, y2),
            xytext=(x1, y1),
            arrowprops={
                "arrowstyle": "-|>",
                "color": ROUTE_COLOR,
                "linewidth": 2.6,
                "shrinkA": 16,
                "shrinkB": 18,
                "mutation_scale": 20
            },
            zorder=6
        )

        ax.text(
            (x1 + x2) / 2,
            (y1 + y2) / 2,
            str(number),
            ha="center",
            va="center",
            fontsize=9,
            fontweight="bold",
            color="#ffffff",
            zorder=7,
            bbox={
                "boxstyle": "circle,pad=0.30",
                "facecolor": ROUTE_COLOR,
                "edgecolor": "#ffffff",
                "linewidth": 1.4
            }
        )

    _build_route_table(figure, ax, segments, start, goal, config)

    _add_header(
        figure,
        f"Rute Optimal {start} → {goal}:  " + " → ".join(route),
        "Nomor pada peta merujuk ke tabel rincian edge di sisi kanan"
    )

    total = segments[-1]["cumulative"] if segments else (0, 0, 0)

    score = (config or {}).get("final_score")

    extra = (
        f"Total {total[0]:.2f} km · {total[1]:.1f} menit · "
        f"{_rupiah(total[2], 2)}"
    )

    if score:

        extra += f" · skor {float(score):.6f}"

    _add_footnote(figure, config, extra)

    figure.savefig(path, dpi=200, facecolor="white")

    plt.close(figure)


def _build_route_table(figure, ax, segments, start, goal, config):
    """Menuliskan tabel rincian edge di sisi kanan gambar."""

    figure_width = figure.get_figwidth()
    figure_height = figure.get_figheight()

    table_ax = figure.add_axes([
        (PAD_IN + 11.0 + 0.35) / figure_width,
        (PAD_IN + FOOTER_IN) / figure_height,
        5.4 / figure_width,
        (figure_height - 2 * PAD_IN - HEADER_IN - FOOTER_IN) / figure_height
    ])

    table_ax.set_axis_off()

    table_ax.set_facecolor("white")

    table_ax.add_patch(
        plt.Rectangle(
            (0.0, 0.0),
            1.0,
            1.0,
            transform=table_ax.transAxes,
            facecolor="#fbfcfd",
            edgecolor="#c9d2dc",
            linewidth=1.0
        )
    )

    lines = ["RINCIAN EDGE RUTE OPTIMAL", "=" * 30]

    for number, segment in enumerate(segments, start=1):

        cumulative = segment["cumulative"]

        lines.append(f"{number}. {segment['from']} → {segment['to']}")
        lines.append(
            f"   jarak   : {segment['distance']:.1f} km"
        )
        lines.append(
            f"   waktu   : {segment['time']:.0f} menit"
        )
        lines.append(
            f"   bbm     : {_rupiah(segment['fuel'])}"
        )
        lines.append(
            f"   kumulatif: {cumulative[0]:.1f} km / "
            f"{cumulative[1]:.0f} mnt / {_rupiah(cumulative[2])}"
        )
        lines.append("")

    total = segments[-1]["cumulative"] if segments else (0, 0, 0)

    lines.append("-" * 30)
    lines.append("TOTAL RUTE")
    lines.append(f"  jarak    : {total[0]:.2f} km")
    lines.append(f"  waktu    : {total[1]:.1f} menit")
    lines.append(f"  biaya bbm: {_rupiah(total[2], 2)}")

    if config:

        lines.append(
            f"  skor     : {float(config['final_score']):.6f}"
        )
        lines.append(
            f"  bobot    : J_W={config['distance_weight']} / "
            f"W_W={config['time_weight']}"
        )

    lines.append("")
    lines.append("-" * 30)
    lines.append("KETERANGAN GAMBAR")
    lines.append(f"  lokasi      : {len(LOCATION_NODES)} titik A-Z")
    lines.append(
        f"  persimpangan: {', '.join(sorted(JUNCTION_NODES)) or 'tidak ada'}"
    )
    lines.append(f"  node hijau  : start ({start})")
    lines.append(f"  node merah  : goal ({goal})")
    lines.append("  berlian oranye: persimpangan (dapat dilalui)")
    lines.append("  garis oranye: edge rute optimal")
    lines.append("  garis tipis : edge lain (abu-abu)")
    lines.append("  angka 1..n  : segmen pada tabel")
    lines.append("")
    lines.append("  edge = ruas jalan dua arah")
    lines.append("  jarak dalam km (DISTANCE)")
    lines.append("  waktu dalam menit (GRAPH)")
    lines.append("  bbm = jarak x (harga bensin / km/L)")

    table_ax.text(
        0.05,
        0.95,
        "\n".join(lines),
        transform=table_ax.transAxes,
        ha="left",
        va="top",
        fontsize=_table_font_size(figure_height, len(lines)),
        family="monospace",
        color="#16222e",
        linespacing=1.28
    )


TABLE_LINE_SPACING = 1.28

TABLE_FONT_LIMIT = 7.9

TABLE_FONT_FLOOR = 4.6


def _table_font_size(figure_height, line_count):
    """Menyesuaikan ukuran font agar seluruh tabel muat di dalam kotak."""

    available_in = figure_height - 2 * PAD_IN - HEADER_IN - FOOTER_IN

    fitted = available_in * 72.0 / (max(line_count, 1) * TABLE_LINE_SPACING)

    return max(TABLE_FONT_FLOOR, min(TABLE_FONT_LIMIT, fitted))


def _is_walkable(nodes):
    """Memeriksa apakah setiap segmen rute benar-benar ada pada graf."""

    for position in range(len(nodes) - 1):

        first, second = nodes[position], nodes[position + 1]

        if second not in GRAPH.get(first, {}):

            return False

    return True


def resolve_route(config, start, goal):
    """Mengambil daftar node rute dari data eksperimen."""

    if not config:

        return [start, goal]

    route_text = config.get("route") or ""

    nodes = [
        part.strip()
        for part in route_text.split("->")
        if part.strip()
    ]

    if len(nodes) < 2:

        return [start, goal]

    if not _is_walkable(nodes):

        return []

    return nodes


def main():
    """Membuat seluruh gambar graf rute."""

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    config = read_experiment()

    start = (config or {}).get("start", "B") or "B"

    goal = (config or {}).get("goal", "N") or "N"

    fuel_price_km = float(
        (config or {}).get("fuel_price_per_liter", 10000)
    ) / float(
        (config or {}).get("km_per_liter", 59.0)
    )

    route = resolve_route(config, start, goal)

    route_pairs = {
        (route[index], route[index + 1])
        for index in range(len(route) - 1)
    }

    degrees = node_degrees()

    edges = enrich_edges(fuel_price_km)

    overview = OUTPUT_DIR / "graf_rute_penuh.png"

    panels = OUTPUT_DIR / "graf_rute_panel.png"

    focus = OUTPUT_DIR / "graf_rute_optimal.png"

    build_overview(
        edges,
        degrees,
        start,
        goal,
        route_pairs,
        config,
        overview
    )

    build_panels(
        edges,
        degrees,
        start,
        goal,
        route_pairs,
        config,
        panels,
        route
    )

    build_route_focus(
        edges,
        degrees,
        start,
        goal,
        route,
        config,
        focus,
        fuel_price_km
    )

    print("Gambar berhasil dibuat:")
    print(" -", overview)
    print(" -", panels)
    print(" -", focus)

    return overview, panels, focus


if __name__ == "__main__":
    main()
