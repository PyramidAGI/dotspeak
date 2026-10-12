"""Plan a web app with login: choose goals and let the program plan the tasks.
Run: python webapp_planner.py

Works like homestead_planner.py, with other files:
webapp_tasks.txt holds the auth, DB and UI tasks, and webapp_world.txt
holds the objects, states and actions.
The scene has one column per sector and one box per object. The colour of
a box shows its state: red for the start state, yellow for a state in
between, green for the last state. A thick border marks the objects the
last task changed, and a star marks a goal. Nothing in the drawing names
a task or an object, so it also works for other world files.

Uses only Python's standard library (Tkinter is required for the window).
"""

import tkinter as tk
from pathlib import Path

from homestead import H, W
from homestead_planner import Planner

HERE = Path(__file__).parent
# (fill, border) for the start state, a state in between, and the last state.
COLORS = (("#f6d5d1", "#b03a2e"), ("#fbe9b7", "#a07d12"), ("#d3edd5", "#2e7d32"))


class WebAppPlanner(Planner):
    task_file = HERE / "webapp_tasks.txt"
    world_file = HERE / "webapp_world.txt"
    title = "Web app planner - auth, DB, UI"

    def reset(self):
        self.changed = set()
        super().reset()

    def do(self, key):
        ready = key not in self.done and not self.unmet(key)
        makes = self.actions.get(key, {"makes": []})["makes"]
        self.changed = {obj for obj, _, _ in makes} if ready else set()
        super().do(key)

    def columns(self):
        """[(sector, objects)]: each object goes to the first sector whose tasks change it."""
        placed, result = set(), []
        for sector, tasks in self.sectors.items():
            objects = [obj for key, _ in tasks if key in self.actions
                       for obj, _, _ in self.actions[key]["makes"]]
            objects = [obj for obj in dict.fromkeys(objects) if obj not in placed]
            placed.update(objects)
            result.append((sector, objects))
        return result

    def draw(self):
        c = self.canvas
        c.delete("all")
        c.create_rectangle(0, 0, W, H, fill="#f7f7fb", width=0)
        goals = dict(self.goals)
        columns = self.columns()
        width = W / len(columns)
        for i, (sector, objects) in enumerate(columns):
            x0, x1 = i * width + 8, (i + 1) * width - 8
            tasks = self.sectors[sector]
            done = sum(k in self.done for k, _ in tasks)
            c.create_text((x0 + x1) / 2, 20, text=f"{sector.upper()}   {done}/{len(tasks)}",
                          font=("Arial", 11, "bold"), fill="#333")
            gap = 6
            box = min(50, (H - 50) / max(len(objects), 1) - gap)
            for j, obj in enumerate(objects):
                y0 = 40 + j * (box + gap)
                y1 = y0 + box
                states = self.objects[obj]
                index = states.index(self.state[obj])
                kind = 0 if index == 0 else 2 if index == len(states) - 1 else 1
                fill, edge = COLORS[kind]
                c.create_rectangle(x0, y0, x1, y1, fill=fill, outline=edge,
                                   width=3 if obj in self.changed else 1)
                c.create_text(x0 + 8, y0 + box * 0.32, text=obj, anchor="w",
                              font=("Arial", 10, "bold"), fill="#222")
                c.create_text(x0 + 8, y0 + box * 0.72, text=self.state[obj], anchor="w",
                              font=("Arial", 9), fill=edge)
                for k in range(len(states)):  # One dot per state, filled up to the current one.
                    x = x1 - 12 - (len(states) - 1 - k) * 12
                    y = y1 - 11
                    c.create_oval(x - 4, y - 4, x + 4, y + 4, outline=edge,
                                  fill=edge if k <= index else "")
                if obj in goals:
                    reached = self.state[obj] == goals[obj]
                    c.create_text(x1 - 6, y0 + 10, text=f"★ {goals[obj]}", anchor="e",
                                  font=("Arial", 8, "bold"),
                                  fill="#2e7d32" if reached else "#7b1fa2")
        if self.labels and len(self.done) == len(self.labels):
            c.create_text(W / 2, H - 14, text="All tasks done", font=("Arial", 12, "bold"),
                          fill="#2e7d32")


def main():
    window = tk.Tk()
    WebAppPlanner(window)
    window.mainloop()


if __name__ == "__main__":
    main()
