from analyze import *
from PIL import Image, ImageDraw, ImageOps

# Primitives needed
# Give me an X by X board
# Add a stone (color) at POS
# Add a number at POS
# Add a title to a board
# Display this collection of X by X boards (with titles)
# Add a title to the collection

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
        pr = 0.8 * PX_PER_INTERSECT
        px, py = PX_PER_INTERSECT * (x+.5), PX_PER_INTERSECT * (y+.5)

        self.draw.chord(((px-pr,py-pr),(px+pr,py+pr)), 0, 360, fill={
            "B": BLACK_COLOR,
            "W": WHITE_COLOR,
        }, outline=OUTLINE_COLOR, width=2)

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
    def __init__(self, boards): # Constraint: All boards must be the same size
        self.boards = boards
        self.title = None
    def add_title(self, title):
        self.title = title
    def save(self, filename):
        pass

with Katago(calc=False):
    # Diagram of first black stone placement (evaluation method)
    # Diagram of first black stone placement (komi method)
    # Diagram of first white stone placement
    one_move = {(size, color, method): DisplayBoard(size) for size in (9,19) for color in "BW" for method in ["komi", "neural"]}
    for size in (9,19):
        base_komi = {19: 6.5, 9: 6}[size]
        
        for position in tqdm(list(Position.all_with_n_stones(1, size)), desc=f"{size}x{size} 1-move positions"):
            move = position.moves[0]
            komi, neural, winrate = position.estimate_score()
            one_move[(size, move.color, "komi")].add_number(komi-base_komi, move.x, move.y)
            one_move[(size, move.color, "neural")].add_number(neural-base_komi, move.x, move.y)
    for (size, color, method), board in one_move.items():
        board.add_title(f"{size}x{size} values, {method} method ({color})")
        board.save(f"{size}x{size}_{method}_{color}.png")

    # Diagram of two-stone placements close to round values

    # Diagram of EVERY two-stone black-black placement
    # Diagram of EVERY two-stone black-white placement
    # Diagram of EVERY two-stone white-white placement

    # Diagram of handicaps values
    # Diagram of komi values
