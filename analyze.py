import sqlitedict
import csv
import functools
import json
import os.path
import subprocess
import sys
import time
import uuid
from tqdm import tqdm

KATAGO=os.path.expanduser("~/KataGo/cpp/katago")
CONFIG=os.path.expanduser("~/KataGo/cpp/default_analysis.cfg")
OUTPUT=os.path.expanduser("~/hack-katago/out.csv")

A9, B9, C9, D9, E9 = (6, 6), (2, 2), (6, 2), (2, 6), (4, 4)
A13, B13, C13, D13, E13, F13, G13, H13, I13 = (9, 9), (3, 3), (9, 3), (3, 9), (6, 6), (3, 6), (9, 6), (6, 9), (6, 3)
A19, B19, C19, D19, E19, F19, G19, H19, I19 = (15, 15), (3, 3), (15, 3), (3, 15), (9, 9), (3, 9), (15, 9), (9, 15), (9, 3)
HANDICAPS = [
    # Guess at small board KOMI (below 19x19)
    (3, ()),
    (4, ()),
    (5, ()),
    (6, ()),
    (7, ()),
    (8, ()),
    (10, ()),
    (11, ()),
    (12, ()),
    (14, ()),
    (15, ()),
    (16, ()),
    (17, ()),
    (18, ()),

    # Guess at point equivalents of handicaps and standard size komi
    (19, ()),
    (19, (A19, B19)),
    (19, (A19, B19, C19)),
    (19, (A19, B19, C19, D19)),
    (19, (A19, B19, C19, D19, E19)),
    (19, (A19, B19, C19, D19,      F19, G19)),
    (19, (A19, B19, C19, D19, E19, F19, G19)),
    (19, (A19, B19, C19, D19,      F19, G19, H19, I19)),
    (19, (A19, B19, C19, D19, E19, F19, G19, H19, I19)),
    (13, ()),
    (13, (A13, B13)),
    (13, (A13, B13, C13)),
    (13, (A13, B13, C13, D13)),
    (13, (A13, B13, C13, D13, E13)),
    (13, (A13, B13, C13, D13,      F13, G13)),
    (13, (A13, B13, C13, D13, E13, F13, G13)),
    (13, (A13, B13, C13, D13,      F13, G13, H13, I13)),
    (13, (A13, B13, C13, D13, E13, F13, G13, H13, I13)),
    (9, ()),
    (9, (A9, B9)),
    (9, (A9, B9, C9)),
    (9, (A9, B9, C9, D9)),
    (9, (A9, B9, C9, D9, E9)),
]

def avg_score(score1, score2):
    score1 = int(score1*2)
    score2 = int(score2*2)
    return int((score1 + score2)/2)/2

class Singleton(type):
    _instances = {}
    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]

@functools.total_ordering
class ComparableByData():
    def __hash__(self):
        return hash(self._data())
    def __eq__(self, other):
        return self._data() == other._data()
    def __lt__(self, other):
        return self._data() < other._data()

def ellipsize(s, max=200):
    if len(s) < max:
        return s
    else:
        return s[:max-3]+"..."

class Katago(metaclass=Singleton):
    def __init__(self, calc=True):
        self.calc = calc

    def __enter__(self):
        self.cache = sqlitedict.SqliteDict("katago.sqlite", autocommit=True)
        command = [KATAGO, "analysis", "-config", CONFIG, "-quit-without-waiting"]
        if self.calc:
            print("Opening katago... ", file=sys.stderr, end="")
            self.proc = subprocess.Popen(command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                text=True,
                bufsize=1,
            )
            print("open", file=sys.stderr)
            ver_info = self.query_json({"id":self.random_id(), "action":"query_version"})
            print(f"katago program version {ver_info["version"]}")
            model_info = self.query_json({"id": self.random_id(), "action":"query_models"})
            print(f"katago model version {model_info["models"][0]["name"]}")
            self.start_time = time.time()
        self.calls = 0

    def random_id(self):
        return str(uuid.uuid4())

    def __exit__(self, type, value, tb):
        self.cache.close()
        if self.calc:
            print("Closing katago... ", file=sys.stderr, end="")
            self.proc.terminate()
            self.proc.wait()
            print("closed", file=sys.stderr)

    @functools.cache
    def _query(self, s: str):
        if s in self.cache:
            #print(f"[cache] send: {s}", file=sys.stderr)
            stdout = self.cache[s]
            #print(f"[cache] recv: {ellipsize(stdout).rstrip()}", file=sys.stderr)
            return stdout
        assert self.calc, "Katago was opened in non-calc mode. Don't do new calculations!"
            
        #print(f"[katago] send: {s}", file=sys.stderr)
        #stdout, stderr = self.proc.communicate(timeout=2)
        self.proc.stdin.write(s+"\n")
        self.proc.stdin.flush()
        stdout = self.proc.stdout.readline()
        #print(f"[katago] recv: {ellipsize(stdout).rstrip()}", file=sys.stderr)
        self.cache[s] = stdout
        #self._call()
        return stdout

    def query_json(self, obj):
        return json.loads(self._query(json.dumps(obj)))

    def _call(self):
        self.calls += 1
        if (self.calls % 1000) == 0:
            elapsed = time.time() - self.start_time
            avg_duration = elapsed / self.calls
            print(f"{self.calls} calls in {avg_duration:.3f}s/call", file=sys.stderr)

class Move(ComparableByData):
    def __init__(self, color, x, y):
        self.color = color
        self.x = x
        self.y = y

    def vertex(self):
        return "ABCDEFGHJKLMNOPQRSTUVWXYZ"[self.x] + str(self.y+1)
    
    def _data(self):
        return (self.color, self.x, self.y)

    def __repr__(self):
        return f"Move({self.color}, {self.x}, {self.y})"

    def __str__(self):
        return f"{self.color}{self.vertex()}"

class Position(ComparableByData):
    def __init__(self, moves, size):
        self.moves = moves
        self.size = size

    def flipped(self):
        moves = []
        for move in self.moves:
            moves.append(Move(move.color, self.size - move.x - 1, move.y))
        return Position(moves, self.size)

    def rotated(self, n):
        moves = self.moves
        for _ in range(n % 4):
            moves, old_moves = [], moves
            for move in old_moves:
                #print("rotate", move, self.size, (move.y, self.size-move.x))
                moves.append(Move(move.color, move.y, self.size - move.x - 1))
        return Position(moves, self.size)

    def canonicalize(self, mirror=True):
        if mirror:
            return min(pos.canonicalize(mirror=False) for pos in self.symmetries())

        # Sort moves lexicographically by (color, x, y)
        return Position(sorted(self.moves), self.size)

    @classmethod
    def all_with_n_stones(cls, n, size):
        if n == 0:
            return [cls([], size)]
        else:
            res = set()
            for p1 in cls.all_with_n_stones(n-1, size):
                for p2 in p1.all_with_added_stone():
                    res.add(p2.canonicalize())
            return sorted(res)

    def all_with_added_stone(self):
        # Find every free intersection
        intersections = {(x, y) for x in range(self.size) for y in range(self.size)}
        for move in self.moves:
            intersections.remove((move.x, move.y))
        for empty in intersections:
            for color in "BW":
                # Technically some board positions are ILLEGAL in go??!
                # but... none of the 2-stone positions, so put off that problem for now
                yield self.with_added_move(Move(color, empty[0], empty[1]))

    def with_added_move(self, move):
        return Position(self.moves + [move], self.size)

    def symmetries(self):
        for flipped in [False, True]:
            if flipped:
                self = self.flipped()
            for n in range(4):
                yield self.rotated(n)

    def query(self, komi=0.0):
        return {
            "id": str(self),
            "initialStones": [[move.color, move.vertex()] for move in self.moves],
            "moves": [],
            "rules": "japanese", # For single-point komi differences
            "komi": komi,
            "overrideSettings": {

            },
            #"initialPlayer": "B",
            "boardXSize": self.size,
            "boardYSize": self.size,
            #"maxVisits": 100, # Sensei's library has evaluations with 1,000,000 for komi estimation
        }

    def estimate_score(self):
        # But... does katago actually accord with that? Testing time! Ans: No. So don't do that.

        # Find komi with close to 50% win rate
        lower, upper = (-150.0, 150.0)
        neural = Katago().query_json(self.query(komi=0.0))["rootInfo"]["scoreLead"]

        while lower + 0.5 < upper:
            middle = avg_score(lower, upper)
            resp = Katago().query_json(self.query(komi=middle))
            score = resp["rootInfo"]["scoreLead"]
            #stddev = resp["rootInfo"]["rawScoreSelfplayStdev"]
            winrate = resp["rootInfo"]["winrate"]
            if winrate < 0.5:
                # Black tends to LOSE, so decrease komi for white
                lower, upper = lower, middle
            else:
                # Back tends to WIN, so increase komi for white
                lower, upper = middle, upper

        winrateLow = Katago().query_json(self.query(komi=lower))["rootInfo"]["winrate"]
        winrateHigh = Katago().query_json(self.query(komi=upper))["rootInfo"]["winrate"]

        if abs(winrateLow - 0.5) < abs(winrateHigh - 0.5):
            komi, winrate = lower, winrateLow
        else:
            komi, winrate = upper, winrateHigh

        return komi, neural, winrate

    def _data(self):
        return (tuple(self.moves), self.size)

    def __repr__(self):
        return f"Position({repr(self.moves)}, size={self.size})"

    def __str__(self):
        return f"Position({self.size}, {self.printable_moves()})"

    def printable_moves(self):
        return " ".join(str(move) for move in self.moves)

HANDICAPS = [
    Position(tuple(Move("B", x, y) for x,y in moves), size) for size, moves in HANDICAPS
]
if __name__ == "__main__":
    with open(OUTPUT, "w", encoding="utf8") as f, Katago() as _:
        fieldnames = ["size", "stones", "score_komi", "score_neural", "winrate_komi"]
        writer = csv.writer(f, quoting=csv.QUOTE_MINIMAL)
        writer.writerow(fieldnames)
        for position in tqdm(HANDICAPS, desc="Handicap Positions"):
            komi, neural, winrate = position.estimate_score()
            writer.writerow([position.size, position.printable_moves(), komi, neural, winrate])
        f.flush()
        for size, max_n in {9: 2, 19: 2}.items():
            for n in range(0,max_n+1):
                count = 0
                for position in tqdm(list(Position.all_with_n_stones(n, size)), desc=f"{size}x{size} {n}-move positions"):
                    count += 1
                    try:
                        komi, neural, winrate = position.estimate_score()
                    except:
                        print(position)
                        raise
                    writer.writerow([position.size, position.printable_moves(), komi, neural, winrate])
                f.flush()
                #print(f"{n}-stone {size}x{size} positions: {count}")
