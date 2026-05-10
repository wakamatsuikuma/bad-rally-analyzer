SYSTEM_INSTRUCTION = """
You analyze badminton match videos.
Return only structured data that matches the provided schema.
Be conservative and deterministic.
""".strip()


USER_PROMPT = """
Analyze the uploaded badminton video and estimate rally-by-rally shot counts.

Definitions:
- A rally starts when the serve is struck to begin live play.
- A rally ends when the shuttle is no longer in play because of a winner, error, net fault, out ball, or umpire stoppage.
- A shot count is the number of player contacts with the shuttle during one rally, including the serve.
- Ignore warm-up, replays, dead time, celebrations, towel breaks, and intervals.
- If a section is ambiguous, choose the most likely estimate and explain it in notes.

Requirements:
- Detect all rallies in the video in chronological order.
- For each rally, estimate start and end timestamps in seconds.
- For each rally, estimate the shot count as an integer.
- Compute the average shots per rally across the entire video.
- Keep notes short and factual.
- If no rally is visible, return total_rallies as 0, average_shots_per_rally as 0, and an empty rallies list.
""".strip()
