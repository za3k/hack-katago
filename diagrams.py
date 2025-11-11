from analyze import *
from PIL import Image, ImageDraw, ImageOps
import itertools

BOARD_COLOR = (220, 178, 92) # sensei's library: 242,176,109
BLACK_COLOR = (0, 0, 0)
WHITE_COLOR = (255, 255, 255)
LINE_COLOR = (0, 0, 0)
OUTLINE_COLOR = (0, 0, 0)
TITLE_BG_COLOR = (255, 255, 255)
TITLE_COLOR = (0, 0, 0)
PX_PER_INTERSECT = 40
TITLE_HEIGHT = PX_PER_INTERSECT

STAR_POINTS = {
    19:  (A19, B19, C19, D19, E19, F19, G19, I19, H19),
    9: (A9, B9, C9, D9, E9),
}
BASE_KOMI = {19: 6.5, 9: 6.5}

def the_one_thats_not(lst, x):
    assert len(lst) == 2
    if lst[0] != x: return lst[0]
    if lst[1] != x: return lst[1]
    assert False

class DisplayBoard():
    def __init__(self, size):
        self.size = size
        self.title = None
        self.intersections = {}
        self.image = Image.new("RGB", (self.size * PX_PER_INTERSECT,)*2, BOARD_COLOR)
        self.draw = ImageDraw.Draw(self.image, "RGB")

        # Draw lines, intersections
        for x in range(self.size):
            px = PX_PER_INTERSECT * (x+.5)
            self.draw.line(xy=[(px, PX_PER_INTERSECT/2), (px, self.image.height-PX_PER_INTERSECT/2)], fill=LINE_COLOR, width=2)
        for y in range(self.size):
            py = PX_PER_INTERSECT * (y+.5)
            self.draw.line(xy=[(PX_PER_INTERSECT/2, py), (self.image.width-PX_PER_INTERSECT/2, py)], fill=LINE_COLOR, width=2)

        # Draw star points
        for x,y in STAR_POINTS[self.size]:
            pr = 0.2 * PX_PER_INTERSECT
            px, py = PX_PER_INTERSECT * (x+.5), PX_PER_INTERSECT * (y+.5)
            self.draw.chord(((px-pr,py-pr),(px+pr,py+pr)), 0, 360, fill=LINE_COLOR)

    def add_stone(self, color, x, y):
        x, y = self.size - x -1, y
        self.intersections[(x, y)] = color
        pr = 0.4 * PX_PER_INTERSECT
        px, py = PX_PER_INTERSECT * (x+.5), PX_PER_INTERSECT * (y+.5)

        self.draw.chord(((px-pr,py-pr),(px+pr,py+pr)), 0, 360, fill={
            "B": BLACK_COLOR,
            "W": WHITE_COLOR,
        }[color], outline=OUTLINE_COLOR, width=2)

    def add_text(self, t, x, y, color="black"):
        x, y = self.size - x -1, y
        self.intersections[(x, y)] = t
        px, py = PX_PER_INTERSECT * (x+.5), PX_PER_INTERSECT * (y+.5)
        bbox, r = self.draw.textbbox((px, py), text=t, anchor="mm", align="center"), 2
        bbox = [bbox[0]-r, bbox[1]-r, bbox[2]+r, bbox[3]+r]
        self.draw.rectangle(bbox, fill=BOARD_COLOR)
        self.draw.text((px, py), text=t, anchor="mm", align="center", fill=color)

    def add_number(self, number, x, y):
        t = "{:+.1f}".format(round(number, 1))
        self.add_text(t, x, y)

    def add_title(self, title):
        if self.title is None:
            newSize = (self.image.width, self.image.height + TITLE_HEIGHT)
            self.image = ImageOps.pad(self.image, newSize, color=TITLE_BG_COLOR, centering=(0,0))
            self.draw = ImageDraw.Draw(self.image, "RGB")
        self.title = title

        center = (self.image.width/2, self.image.height-TITLE_HEIGHT/2)
        self.draw.text(center, text=title, anchor="mm", align="center", fill=TITLE_COLOR)

    def save(self, filename):
        self.image.save(filename)

class DisplayCollection():
    def __init__(self, boards, title):
        self.boards = boards
        images = [b.image for b in self.boards]
        self.title = None
        TRANSPARENT = (0,0,0,0)

        # Vertical always.
        width = max(i.width for i in images)

        title_im = Image.new("RGBA", (width, TITLE_HEIGHT), "white")
        center = (width/2, TITLE_HEIGHT/2)
        ImageDraw.Draw(title_im).text(center, text=title, anchor="mm", align="center", fill=TITLE_COLOR)
        images.insert(0, title_im)

        height = sum(i.height for i in images)
        self.image = Image.new("RGBA", (width, height), TRANSPARENT)

        y = 0
        for i in images:
            self.image.paste(i, (0, y))
            y += i.height

    def save(self, filename):
        self.image.save(filename)

with Katago(calc=False):
    # Diagram of first black stone placement (evaluation method)
    # Diagram of first black stone placement (komi method)
    # Diagram of first white stone placement
    one_move = {(size, color, method): DisplayBoard(size) for size in (9,19) for color in "BW" for method in ["komi", "neural"]}
    for size in (9,19):
        for position in tqdm(list(Position.all_with_n_stones(1, size)), desc=f"{size}x{size} 1-move positions"):
            move = position.moves[0]
            komi, neural, winrate = position.estimate_score()
            one_move[(size, move.color, "komi")].add_number(komi-BASE_KOMI[size], move.x, move.y)
            one_move[(size, move.color, "neural")].add_number(neural-BASE_KOMI[size], move.x, move.y)
    for (size, color, method), board in one_move.items():
        board.add_title(f"{size}x{size} values, {method} method ({color})")
        board.save(f"{size}x{size}_{method}_{color}.png")

    # Diagram of EVERY two-stone black-black placement
    # Diagram of EVERY two-stone black-white placement
    # Diagram of EVERY two-stone white-white placement
    for size in [9,19]:
        boards = {
            0: {},
            1: {},
            2: {},
        }
        for position in tqdm(list(Position.all_with_n_stones(2, size)), desc=f"{size}x{size} 2-stone positions"):
            whites = [move.color for move in position.moves].count("W")
            komi, neural, winrate = position.estimate_score()
            for b in position.symmetries():
                for first_move in b.moves:
                    if first_move.color == "W" and whites < 2: continue
                    second_move = the_one_thats_not(b.moves, first_move)
                    if first_move not in boards[whites]:
                        B = DisplayBoard(size)
                        B.add_stone(first_move.color, first_move.x, first_move.y)
                        boards[whites][first_move] = B
                    boards[whites][first_move].add_number(komi-BASE_KOMI[size], second_move.x, second_move.y)

        for whites, bs in boards.items():
            x = {
                0: "black-black",
                1: "black-white",
                2: "white-white",
            }[whites]
            title = f"{size}x{size} 2-stone positions ({x})"
            coll = DisplayCollection(bs.values(), title=title)
            coll.save(f"{size}x{size}_komi_{x}.png")

    # Diagram of starting placements close to round values
    for size in [9,19]:
        closest = {}
        for position in tqdm(list(itertools.chain.from_iterable(Position.all_with_n_stones(n, size) for n in range(3))), desc=f"{size}x{size} point equivalents"):
            komi, neural, winrate = position.estimate_score()
            off = abs(winrate-0.5)
            res = closest.get(komi)
            if res is None or res[0] > off:
                closest[komi] = (off, position, winrate)
        boards = []
        for (komi, (off, position, winrate)) in sorted(closest.items(), key=lambda x: x[0]):
            board = DisplayBoard(size)
            for move in position.moves:
                board.add_stone(move.color, move.x, move.y)
            if int(komi) != komi: continue
            board.add_title(f"{komi} points ({winrate*100:.5f}% win rate)")
            boards.append(board)
        coll = DisplayCollection(boards, title="point value, closest handicap equivalents")
        coll.save(f"{size}x{size}_point_equivalents.png")

    with open("charts.md", "w") as f:
        # Diagram of handicaps values
        print("| size | handicap | value estimate (winrate) | value estimate (neural) |", file=f)
        print("|------|----------|--------------------------|-------------------------|", file=f)
        for position in tqdm(HANDICAPS, desc="Handicaps"):
            if position.size in [9,13,19]:
                komi, neural, _ = position.estimate_score()
                handicap = max(1, len(position.moves))
                print(f"| {position.size} | {handicap} | {komi:+.1f} | {neural:+.1f} |", file=f)
        print(file=f)

        # Diagram of komi values
        print("| size | komi estimate (winrate) | komi estimate (neural) |", file=f)
        print("|------|-------------------------|------------------------|", file=f)
        for size in tqdm(range(3, 20), desc="Komi"):
            position = Position([], size)
            komi, neural, _ = position.estimate_score()
            print(f"| {size} | {komi:+.1f} | {neural:+.1f} |", file=f)
        print(file=f)
