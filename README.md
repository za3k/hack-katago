Analysis:
- Evaluate the score of every possible 0 stone, 1-stone, 2-stone, position using katago.
- Two methods were used:
    - Simple board value estimation
    - Bisection, finding the komi which gave results closest to 50% win rate for black + white.
- We then stored that data in high precision to `out.csv`

Software used
- Katago v1.16.4
- Model kata1-b28c512nbt-adam-s11165M-d5387M
- Japanese scoring
- 500 max visits (default)

`diagram.py` uses the database cache (equivalent to CSV) to draw some human-readable diagrams of the results.

All diagrams are relative to 6.5 komi.
