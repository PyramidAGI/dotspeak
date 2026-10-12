"""Build a homestead from the tasks in periodperiod.txt. Run: python homestead.py

The program reads the construction, transport and agriculture tasks
from periodperiod.txt. Each task is a button. Click a button to do the task.
homestead_world.txt describes the world as objects with states, and each
task as an action that needs some states and changes others. A task is
ready when the states it needs are true. Point at a button to see what it needs.
The scene shows the current state of each object: the truck brings stone
for the house, the harvest feeds the cattle, and the house gets walls,
a window and a roof. When all tasks are done, the homestead is complete.
Hint shows a task that is ready. Reset starts again.

Uses only Python's standard library (Tkinter is required for the window).
Drawings are a simple visual model, not construction or farming advice.
"""

import re
import tkinter as tk
from pathlib import Path
from tkinter import ttk

TASK_FILE = Path(__file__).with_name("periodperiod.txt")
WORLD_FILE = Path(__file__).with_name("homestead_world.txt")
W, H = 760, 540
GROUND, ROAD = 300, 440
SKY, BG = "#bfe3f5", "#f5f3ee"


def task_key(name):
    """'3. to-repair cracked wall' -> 'repair cracked wall'."""
    return re.sub(r"^to[-_]\s*", "", re.sub(r"^\d+\.\s*", "", name.strip()))


def load_world(path=WORLD_FILE):
    """Return (objects, actions) from the world file.

    objects: {object: [states]}; the first state is the start state.
    actions: {task: {"needs": [(object, state)], "makes": [(object, from, to)]}}
    """
    objects, actions, action = {}, {}, None
    for number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue

        def known(obj, *states):
            obj = obj.strip()
            states = tuple(s.strip() for s in states)
            for state in states:
                if state not in objects.get(obj, []):
                    raise ValueError(f"{path.name} line {number}: unknown state {obj} = {state}")
            return (obj, *states)

        field, _, rest = line.partition(":")
        if ":" not in line:
            action = actions.setdefault(task_key(line), {"needs": [], "makes": []})
        elif field == "needs" and action is not None:
            for part in rest.split(","):
                obj, _, state = part.partition("=")
                action["needs"].append(known(obj, state))
        elif field == "makes" and action is not None:
            for part in rest.split(","):
                obj, _, change = part.partition(":")
                start, _, end = change.partition("->")
                action["makes"].append(known(obj, start, end))
        else:
            objects[field.strip()] = [s.strip() for s in rest.split(",")]
    return objects, actions


def load_sectors(path=TASK_FILE):
    """Return {sector: [(key, label), ...]} from the task file."""
    sectors, current = {}, None
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        if line.endswith("sector"):
            current = line.removesuffix("sector").strip()
            if current == current.lower():  # "auth" -> "Auth"; keep "DB" and "UI".
                current = current.capitalize()
            sectors[current] = []
        elif current:
            label = re.sub(r"^\d+\.\s*", "", line)
            sectors[current].append((task_key(label), label))
    return sectors


class Homestead:
    def __init__(self, window):
        self.sectors = load_sectors()
        self.labels = {key: label for tasks in self.sectors.values() for key, label in tasks}
        self.objects, self.actions = load_world()
        self.state, self.done, self.moves = {}, set(), 0
        window.title("Homestead - construction, transport, agriculture")
        window.configure(bg=BG)

        self.canvas = tk.Canvas(window, width=W, height=H, highlightthickness=0)
        self.canvas.grid(row=0, column=0, padx=12, pady=12)
        panel = tk.Frame(window, bg=BG)
        panel.grid(row=0, column=1, sticky="n", padx=(0, 12), pady=12)

        self.notebook = ttk.Notebook(panel)
        self.notebook.pack()
        self.tabs, self.buttons = {}, {}
        for sector, tasks in self.sectors.items():
            tab = tk.Frame(self.notebook, bg=BG, padx=6, pady=6)
            self.notebook.add(tab, text=sector)
            self.tabs[sector] = tab
            for key, label in tasks:
                button = tk.Button(tab, anchor="w", width=30,
                                   command=lambda k=key: self.do(k))
                button.pack(fill="x", pady=1)
                button.bind("<Enter>", lambda _e, k=key: self.explain(k))
                self.buttons[key] = button

        self.progress = ttk.Progressbar(panel, length=260, maximum=len(self.labels))
        self.progress.pack(pady=(10, 2))
        self.count = tk.StringVar()
        tk.Label(panel, textvariable=self.count, bg=BG).pack()
        controls = tk.Frame(panel, bg=BG)
        controls.pack(pady=8)
        tk.Button(controls, text="Hint", width=10, command=self.hint).pack(side="left", padx=4)
        tk.Button(controls, text="Reset", width=10, command=self.reset).pack(side="left", padx=4)

        self.status = tk.StringVar()
        tk.Label(window, textvariable=self.status, bg=BG, anchor="w", justify="left",
                 wraplength=W + 280, font=("Arial", 11)).grid(
            row=1, column=0, columnspan=2, sticky="we", padx=12, pady=(0, 12))
        self.reset()

    # --- rules ---------------------------------------------------------

    def conditions(self, key):
        """States that must be true before the action: its needs and its "from" states."""
        action = self.actions.get(key, {"needs": [], "makes": []})
        return action["needs"] + [(obj, start) for obj, start, _ in action["makes"]]

    def unmet(self, key):
        return [(obj, state) for obj, state in self.conditions(key) if self.state[obj] != state]

    def ready(self):
        return [k for k in self.labels if k not in self.done and not self.unmet(k)]

    def makers(self, obj, state):
        return [k for k, action in self.actions.items() if k in self.labels
                and any(o == obj and end == state for o, _, end in action["makes"])]

    def describe(self, conditions):
        parts = []
        for obj, state in conditions:
            by = ", ".join(self.labels[k] for k in self.makers(obj, state))
            parts.append(f"{obj} = {state} (now {self.state[obj]}"
                         + (f"; by {by})" if by else ")"))
        return ";  ".join(parts)

    def names(self, keys):
        return ", ".join(self.labels[k] for k in keys)

    def sector_of(self, key):
        return next(s for s, tasks in self.sectors.items() if key in dict(tasks))

    # --- actions -------------------------------------------------------

    def do(self, key):
        if key in self.done:
            return
        unmet = self.unmet(key)
        if unmet:
            self.canvas.bell()
            self.status.set(f"Not yet. Needs: {self.describe(unmet)}")
            return
        before = set(self.ready())
        for obj, _, end in self.actions.get(key, {"makes": []})["makes"]:
            self.state[obj] = end
        self.done.add(key)
        self.moves += 1
        if len(self.done) == len(self.labels):
            self.status.set(f"The homestead is complete in {self.moves} moves!")
        else:
            unlocked = [k for k in self.ready() if k not in before]
            extra = f"  ·  Now possible: {self.names(unlocked)}" if unlocked else ""
            self.status.set(f"Done: {self.labels[key]}{extra}")
        self.refresh()

    def explain(self, key):
        if key in self.done:
            self.status.set(f"Already done: {self.labels[key]}")
        elif self.unmet(key):
            self.status.set(f"{self.labels[key]} needs: {self.describe(self.unmet(key))}")
        else:
            self.status.set(f"Ready: {self.labels[key]}")

    def hint(self):
        ready = self.ready()
        if not ready:
            self.status.set("Nothing left to do. Press Reset to build again.")
            return

        # Prefer a task whose results other open tasks need.
        def unlocks(key):
            made = {(obj, end) for obj, _, end in self.actions.get(key, {"makes": []})["makes"]}
            return sum(bool(made & set(self.conditions(k)))
                       for k in self.labels if k not in self.done)

        key = max(ready, key=unlocks)
        self.notebook.select(self.tabs[self.sector_of(key)])
        self.buttons[key].focus_set()
        self.status.set(f"Hint: {self.labels[key]}")

    def reset(self):
        self.state = {obj: states[0] for obj, states in self.objects.items()}
        self.done.clear()
        self.moves = 0
        self.status.set("Click a task. Point at a task to see what it needs.")
        self.refresh()

    def refresh(self):
        for key, button in self.buttons.items():
            label = self.labels[key]
            if key in self.done:
                button.config(text=f"✓  {label}", fg="#2e7d32", relief="flat", bg="#e3efe0")
            elif self.unmet(key):
                button.config(text=f"·  {label}", fg="#9a9a9a", relief="raised", bg="#ecebe7")
            else:
                button.config(text=f"▶  {label}", fg="#000000", relief="raised", bg="#ffffff")
        for sector, tasks in self.sectors.items():
            n = sum(k in self.done for k, _ in tasks)
            self.notebook.tab(self.tabs[sector], text=f"{sector} {n}/{len(tasks)}")
        self.progress["value"] = len(self.done)
        self.count.set(f"{len(self.done)} / {len(self.labels)} tasks  ·  {self.moves} moves")
        self.draw()

    # --- drawing: each picture shows the current state of an object ------

    def draw(self):
        c, s = self.canvas, self.state.get
        c.delete("all")
        c.create_rectangle(0, 0, W, GROUND, fill=SKY, width=0)
        c.create_oval(660, 30, 710, 80, fill="#ffd54f", outline="")
        c.create_rectangle(0, GROUND, W, ROAD, fill="#9cc77a", width=0)
        c.create_rectangle(0, ROAD, W, H, fill="#6b6b6b", width=0)
        c.create_line(0, 527, W, 527, fill="#e0e0e0", dash=(18, 12), width=2)
        for x, anchor, text in ((20, "w", "CONSTRUCTION"), (W - 10, "e", "AGRICULTURE")):
            c.create_text(x, ROAD - 6, text=text, anchor=anchor, fill="#3d5a2a",
                          font=("Arial", 9, "bold"))
        c.create_text(W - 10, ROAD + 14, text="TRANSPORT", anchor="e",
                      fill="#e0e0e0", font=("Arial", 9, "bold"))
        self.draw_site(c, s)
        self.draw_farm(c, s)
        self.draw_truck(c, s)
        if len(self.done) == len(self.labels):
            c.create_rectangle(190, 40, 570, 100, fill="#fffbe6", outline="#c9a227", width=3)
            c.create_text(380, 70, text="Homestead complete!",
                          font=("Arial", 22, "bold"), fill="#6d5a12")

    def draw_site(self, c, s):
        if s("wall.height") == "none":
            if s("floor") == "level":
                c.create_rectangle(60, 384, 300, 400, fill="#a0784f", width=0)
            else:
                bumps = [v for i, x in enumerate(range(60, 301, 20))
                         for v in (x, 376 if i % 2 else 390)]
                c.create_polygon(*bumps, 300, 400, 60, 400, fill="#a0784f")
            c.create_text(180, 412, text="empty ground", fill="#3d5a2a")
            if s("stone.location") == "site":
                for i in range(5):  # Delivered stone, waiting to become a wall.
                    x = 70 + i * 22
                    c.create_rectangle(x, 360, x + 20, 376, fill="#b9b2a2", outline="#736c60")
        else:
            top = 230 if s("wall.height") == "high" else 310
            c.create_rectangle(55, 395, 305, 405, fill="#8d8d8d", width=0)
            c.create_rectangle(70, top, 290, 395, fill="#d9c7a3", outline="#8a7a5a")
            for i, y in enumerate(range(top + 15, 395, 15)):
                c.create_line(70, y, 290, y, fill="#b8a684")
                for x in range(85 + (i % 2) * 15, 290, 30):
                    c.create_line(x, y - 15, x, y, fill="#b8a684")
            door = "#8b3a2b" if s("door") == "painted" else "#c8c2b4"
            c.create_rectangle(160, 335, 200, 395, fill=door, outline="#5a4a3a")
            c.create_oval(190, 363, 195, 368, fill="#3a3a3a")
            if s("wall.height") == "high":
                self.draw_upper(c, s)
        if s("timber") != "used":  # Timber pile; it becomes the beam.
            sanded = s("timber") == "sanded"
            for i in range(3):
                y = 372 + i * 9
                c.create_rectangle(318, y, 372, y + 8, fill="#d9b98a" if sanded else "#9c7449",
                                   outline="#5e4426")
                if not sanded:
                    c.create_line(322, y + 4, 330, y + 2, 340, y + 5, 352, y + 3, 368, y + 5,
                                  fill="#5e4426")
            c.create_text(345, 412, text="timber", fill="#3d5a2a")

    def draw_upper(self, c, s):
        if s("wall.surface") == "cracked":
            c.create_line(245, 245, 254, 268, 246, 290, 258, 318, fill="#3a2a1a", width=2)
        if s("pipe") == "insulated":
            c.create_line(62, 240, 62, 395, fill="#a0a0a0", width=9)
        else:
            c.create_line(62, 240, 62, 395, fill="#c46a2c", width=3)
        if s("window") != "none":
            c.create_rectangle(100, 255, 145, 300, fill="#cfeefc", outline="#5a4a3a", width=2)
            c.create_line(122, 255, 122, 300, fill="#5a4a3a")
            c.create_line(100, 277, 145, 277, fill="#5a4a3a")
            if s("window") == "dirty":
                for x, y in ((106, 262), (128, 268), (112, 285), (134, 290), (138, 260)):
                    c.create_oval(x, y, x + 7, y + 5, fill="#8a7a5a", outline="")
        if s("beam") == "strong":
            c.create_rectangle(60, 222, 300, 231, fill="#8b5a2b", outline="#4e3218")
            for x in (70, 290):
                c.create_line(x, 231, x + (15 if x < 180 else -15), 250, fill="#8b5a2b", width=4)
        elif s("beam") == "weak":
            c.create_line(60, 225, 180, 233, 300, 225, fill="#b08a5a", width=7)
        if s("bolt") == "tight":
            c.create_oval(176, 222, 184, 230, fill="#9a9a9a", outline="#555")
        elif s("bolt") == "loose":
            c.create_oval(178, 208, 190, 220, fill="#d84315", outline="#555")
            c.create_text(200, 212, text="loose", anchor="w", font=("Arial", 8), fill="#d84315")
        if s("roof") != "none":
            c.create_polygon(45, 222, 180, 140, 315, 222, fill="#a6402e", outline="#6e2a1e")
            for y in (165, 190, 210):
                half = (y - 140) * 135 / 82
                c.create_line(180 - half, y, 180 + half, y, fill="#7e3022")
            if s("tile") == "broken":
                c.create_polygon(205, 172, 225, 176, 214, 188, fill=SKY, outline="#6e2a1e")
            if s("roof") == "leaking":
                for y in (240, 258, 276):
                    c.create_oval(228, y, 234, y + 9, fill="#4a90d9", outline="")

    def draw_farm(self, c, s):
        # Field: soil colour shows water and fertilizer.
        watered = s("soil.moisture") == "watered"
        fertilized = s("soil.nutrients") == "fertilized"
        soil = {(True, True): "#4e3420", (True, False): "#6f5236",
                (False, True): "#a8824f", (False, False): "#cdb07a"}[watered, fertilized]
        c.create_rectangle(390, 340, 560, 428, fill=soil, outline="#7a5a3a")
        if not watered:
            for x, y in ((400, 360), (450, 400), (500, 355), (420, 415)):
                c.create_line(x, y, x + 12, y + 6, x + 8, y + 14, fill="#8a6a3a")
        if s("soil.structure") == "aerated":
            for x in range(398, 556, 14):
                for y in range(352, 426, 14):
                    c.create_oval(x, y, x + 2, y + 2, fill="#2e1e10", outline="")
        else:
            for y in range(350, 428, 8):
                c.create_line(392, y, 558, y, fill="#9a7a4a")
        if s("field") == "flooded":
            c.create_oval(480, 385, 556, 424, fill="#5aa0d8", outline="#3a7ab0")
        for x in range(398, 556, 12):
            if s("wheat") == "harvested":
                c.create_line(x, 340, x, 334, fill="#c9a227", width=2)
            else:
                c.create_line(x, 340, x, 312, fill="#c9a227", width=2)
                c.create_oval(x - 3, 304, x + 3, 316, fill="#e6be3a", outline="")
        if s("hay") == "bale":
            c.create_rectangle(528, 314, 556, 334, fill="#e6be3a", outline="#9a7a1a")

        # Seedbed and vine.
        c.create_rectangle(570, 392, 630, 428, fill="#6f5236", outline="#4e3420")
        for x in range(576, 628, 10):
            if s("seedbed") == "weeded":
                c.create_line(x, 420, x, 412, fill="#4caf50", width=2)
            else:
                c.create_line(x, 426, x - 4, 396, x + 3, 386, fill="#3e7a2a", width=2)
        c.create_line(600, 300, 600, 385, fill="#6d4c2b", width=3)
        c.create_line(580, 320, 620, 320, fill="#6d4c2b", width=2)
        pruned = s("vine") == "pruned"
        leaves = ((592, 310), (604, 314), (586, 326), (612, 330)) if pruned else \
            [(x, y) for x in range(574, 630, 9) for y in range(298, 382, 11)]
        for x, y in leaves:
            c.create_oval(x - 5, y - 5, x + 5, y + 5, fill="#558b2f", outline="#33691e")
        if pruned:
            for x, y in ((596, 334), (606, 338)):
                c.create_oval(x - 3, y - 3, x + 3, y + 3, fill="#6a1b9a", outline="")

        # Stable and animals.
        c.create_rectangle(645, 240, 745, 320, fill="#8d5b3a", outline="#5a3a22")
        c.create_polygon(637, 242, 695, 205, 753, 242, fill="#6d3f24", outline="#4a2a16")
        c.create_rectangle(680, 280, 710, 320, fill="#5a3a22")
        if s("stable") == "dirty":
            for x, y in ((655, 322), (690, 326), (725, 323), (705, 330)):
                c.create_oval(x, y, x + 14, y + 6, fill="#5d4030", outline="")
        c.create_oval(645, 350, 690, 375, fill="#7b4a2a", outline="#3e2a1a")  # cow
        c.create_oval(682, 342, 698, 358, fill="#7b4a2a", outline="#3e2a1a")
        for x in (652, 662, 674, 684):
            c.create_line(x, 372, x, 388, fill="#3e2a1a", width=3)
        if s("cattle") == "fed":
            c.create_rectangle(700, 368, 730, 386, fill="#e6be3a", outline="#9a7a1a")
        else:
            c.create_text(668, 340, text="hungry", font=("Arial", 8), fill="#b71c1c")
        r = 9 if s("sheep") == "shorn" else 16  # sheep
        c.create_oval(712 - r, 410 - r, 712 + r, 410 + r, fill="#fafafa", outline="#9e9e9e")
        c.create_oval(712 + r - 4, 400, 712 + r + 8, 412, fill="#424242")
        if s("wool") == "shorn":
            c.create_rectangle(733, 420, 752, 432, fill="#fafafa", outline="#9e9e9e")

    def draw_truck(self, c, s):
        if s("road") == "blocked":
            c.create_polygon(400, 505, 410, 472, 432, 466, 446, 486, 440, 505,
                             fill="#8a8172", outline="#5a5446")
        tx = 120 if s("truck.position") == "site" else 470
        c.create_rectangle(tx, 455, tx + 110, 490, fill="#3f6fb0", outline="#24426b")
        c.create_rectangle(tx + 112, 445, tx + 162, 490, fill="#d04a3a", outline="#7a2a20")
        c.create_rectangle(tx + 138, 450, tx + 158, 468, fill="#cfeefc", outline="#7a2a20")
        if s("windshield") == "dirty":
            for x, y in ((141, 453), (150, 459), (144, 462)):
                c.create_oval(tx + x, y, tx + x + 5, y + 4, fill="#8a7a5a", outline="")
        if s("vehicle.body") == "damaged":
            c.create_line(tx + 116, 474, tx + 124, 480, tx + 130, 472, tx + 136, 482,
                          fill="#4a1a12", width=2)
        full = s("tank") == "full"
        c.create_text(tx + 125, 458, text="F" if full else "E",
                      fill="#ffffff" if full else "#ffeb3b", font=("Arial", 9, "bold"))
        if s("engine") == "overheated":
            for dx, y, r in ((168, 446, 5), (176, 436, 7), (170, 424, 8)):
                c.create_oval(tx + dx - r, y - r, tx + dx + r, y + r, fill="#e8e8e8", outline="")
        if s("stone.location") == "truck":
            for i in range(3):
                x = tx + 6 + i * 34
                if i == 2 and s("cargo") == "loose":
                    c.create_polygon(x + 8, 452, x + 34, 446, x + 30, 420, x + 4, 426,
                                     fill="#b9b2a2", outline="#736c60")
                else:
                    c.create_rectangle(x, 425, x + 30, 455, fill="#b9b2a2", outline="#736c60")
            if s("cargo") == "secured":
                c.create_line(tx, 438, tx + 110, 438, fill="#3a3a3a", width=3)
        for i, x in enumerate((tx + 22, tx + 88, tx + 142)):
            if i == 1 and s("tire") == "flat":
                c.create_oval(x - 15, 500, x + 15, 514, fill="#222", outline="")
            else:
                c.create_oval(x - 12, 490, x + 12, 514, fill="#222", outline="")
                c.create_oval(x - 4, 498, x + 4, 506, fill="#9a9a9a", outline="")
        if s("brake") == "worn":
            c.create_text(tx + 22, 524, text="worn brake", fill="#ff8a65", font=("Arial", 8))


def main():
    window = tk.Tk()
    Homestead(window)
    window.mainloop()


if __name__ == "__main__":
    main()
