"""Plan a homestead: choose goals and let the program plan the tasks.
Run: python homestead_planner.py

Uses the same files as homestead.py: periodperiod.txt for the tasks and
homestead_world.txt for the objects, states and actions.
Choose goal states, for example roof = sealed, or use a preset.
The planner searches backward from the goals. For each goal state it finds
a task that makes that state, and plans that task's needs first. The plan
holds only tasks that help reach the goals.
Each step has a stage. Steps in the same stage do not depend on each other,
so different crews could do them at the same time.
Click a step to see why it is in the plan. Step does the next task,
Run does the remaining tasks one after the other, Reset starts again.

Uses only Python's standard library (Tkinter is required for the window).
"""

import tkinter as tk
from collections import Counter
from tkinter import ttk

from homestead import BG, TASK_FILE, W, WORLD_FILE, Homestead, load_sectors, load_world


def conditions(action):
    """States that must be true before the action: its needs and its "from" states."""
    return action["needs"] + [(obj, start) for obj, start, _ in action["makes"]]


def make_plan(actions, state, goals, skip=()):
    """Return the task keys that reach all goal states from state, or None.

    To reach a state, pick a task that makes it, first reach that task's
    conditions, then do the task. Tasks in skip are not used again.
    """
    state, steps, used = dict(state), [], set(skip)

    def achieve(obj, want, path):
        if state[obj] == want:
            return True
        if (obj, want) in path:  # Needs itself: give up on this route.
            return False
        path = path | {(obj, want)}
        for key, action in actions.items():
            if key in used or (obj, want) not in [(o, end) for o, _, end in action["makes"]]:
                continue
            saved_state, saved_steps, saved_used = dict(state), len(steps), set(used)
            need, ok = conditions(action), False
            for _ in range(3):  # Reaching one condition can undo another; try again.
                if not all(achieve(o, s, path) for o, s in need):
                    break
                if all(state[o] == s for o, s in need):
                    ok = True
                    break
            if ok:
                for o, _, end in action["makes"]:
                    state[o] = end
                steps.append(key)
                used.add(key)
                return True
            state.clear()  # This task does not work out: undo its part of the plan.
            state.update(saved_state)
            del steps[saved_steps:]
            used.clear()
            used.update(saved_used)
        return False

    for _ in range(3):
        if not all(achieve(o, s, frozenset()) for o, s in goals):
            return None
        if all(state[o] == s for o, s in goals):
            return steps
    return None


def stages(actions, state, steps):
    """Stage of each step: one more than the latest step it depends on."""
    made_at = {(obj, s): 0 for obj, s in state.items()}
    result = []
    for key in steps:
        action = actions[key]
        stage = 1 + max((made_at.get(c, 0) for c in conditions(action)), default=0)
        for obj, _, end in action["makes"]:
            made_at[obj, end] = stage
        result.append(stage)
    return result


def by_stage(actions, state, steps):
    """Sort the steps by stage, if the tasks can still be done in that order."""
    order = sorted(steps, key=dict(zip(steps, stages(actions, state, steps))).get)
    state = dict(state)
    for key in order:
        if any(state[o] != s for o, s in conditions(actions[key])):
            return steps
        for obj, _, end in actions[key]["makes"]:
            state[obj] = end
    return order


def final_state(actions, state):
    """The state after doing every task that can be done, in any order."""
    state, left = dict(state), dict(actions)
    while True:
        key = next((k for k, a in left.items()
                    if all(state[o] == s for o, s in conditions(a))), None)
        if key is None:
            return state
        for obj, _, end in left.pop(key)["makes"]:
            state[obj] = end


class Planner(Homestead):
    """Uses the rules and drawing of the game, with a goal and plan panel.

    Subclasses can plan another world: set the files and title, and override draw().
    """

    task_file, world_file, title = TASK_FILE, WORLD_FILE, "Homestead planner"

    def __init__(self, window):
        self.window = window
        self.sectors = load_sectors(self.task_file)
        self.labels = {key: label for tasks in self.sectors.values() for key, label in tasks}
        self.objects, actions = load_world(self.world_file)
        self.actions = {k: a for k, a in actions.items() if k in self.labels}
        self.state, self.done, self.moves = {}, set(), 0
        self.goals, self.plan, self.plan_stages, self.running = [], [], [], None
        window.title(self.title)
        window.configure(bg=BG)

        self.canvas = tk.Canvas(window, width=W, height=540, highlightthickness=0)
        self.canvas.grid(row=0, column=0, padx=12, pady=12)
        panel = tk.Frame(window, bg=BG)
        panel.grid(row=0, column=1, sticky="n", padx=(0, 12), pady=12)

        goal_box = tk.LabelFrame(panel, text="Goals", bg=BG, padx=6, pady=6)
        goal_box.pack(fill="x")
        presets = tk.Frame(goal_box, bg=BG)
        presets.pack(fill="x")
        tk.Button(presets, text="Everything", command=self.preset).pack(side="left", padx=(0, 4))
        for sector in self.sectors:
            tk.Button(presets, text=sector,
                      command=lambda s=sector: self.preset(s)).pack(side="left", padx=(0, 4))
        picker = tk.Frame(goal_box, bg=BG)
        picker.pack(fill="x", pady=6)
        self.goal_object = ttk.Combobox(picker, values=sorted(self.objects),
                                        state="readonly", width=16)
        self.goal_object.pack(side="left")
        self.goal_object.bind("<<ComboboxSelected>>", self.pick_object)
        tk.Label(picker, text="=", bg=BG).pack(side="left", padx=2)
        self.goal_state = ttk.Combobox(picker, state="readonly", width=11)
        self.goal_state.pack(side="left")
        tk.Button(picker, text="Add", command=self.add_goal).pack(side="left", padx=(4, 0))
        self.goal_list = tk.Listbox(goal_box, height=6, width=44, activestyle="none")
        self.goal_list.pack(fill="x")
        goal_buttons = tk.Frame(goal_box, bg=BG)
        goal_buttons.pack(fill="x", pady=(4, 0))
        tk.Button(goal_buttons, text="Remove", command=self.remove_goal).pack(side="left")
        tk.Button(goal_buttons, text="Clear", command=self.clear_goals).pack(side="left", padx=4)

        plan_box = tk.LabelFrame(panel, text="Plan", bg=BG, padx=6, pady=6)
        plan_box.pack(fill="x", pady=(10, 0))
        lines = tk.Frame(plan_box, bg=BG)
        lines.pack(fill="x")
        self.plan_list = tk.Listbox(lines, height=14, width=44, activestyle="none")
        self.plan_list.pack(side="left", fill="x", expand=True)
        scroll = tk.Scrollbar(lines, command=self.plan_list.yview)
        scroll.pack(side="left", fill="y")
        self.plan_list.config(yscrollcommand=scroll.set)
        self.plan_list.bind("<<ListboxSelect>>", self.why)
        plan_buttons = tk.Frame(plan_box, bg=BG)
        plan_buttons.pack(pady=(6, 0))
        for text, command in (("Step", self.step), ("Run", self.run), ("Reset", self.reset)):
            tk.Button(plan_buttons, text=text, width=9, command=command).pack(side="left", padx=3)

        self.status = tk.StringVar()
        tk.Label(window, textvariable=self.status, bg=BG, anchor="w", justify="left",
                 wraplength=W + 330, font=("Arial", 11)).grid(
            row=1, column=0, columnspan=2, sticky="we", padx=12, pady=(0, 12))
        self.reset()

    # --- goals ---------------------------------------------------------

    def preset(self, sector=None):
        """Goal: every object the sector's tasks change, in its finished state."""
        start = {obj: states[0] for obj, states in self.objects.items()}
        final = final_state(self.actions, start)
        keys = self.labels if sector is None else dict(self.sectors[sector])
        changed = {obj for k in keys if k in self.actions
                   for obj, _, _ in self.actions[k]["makes"]}
        self.goals = [(obj, final[obj]) for obj in self.objects
                      if obj in changed and final[obj] != start[obj]]
        self.make()

    def pick_object(self, _event=None):
        states = self.objects[self.goal_object.get()]
        self.goal_state.config(values=states)
        self.goal_state.set(states[-1])

    def add_goal(self):
        obj, state = self.goal_object.get(), self.goal_state.get()
        if not obj or not state:
            self.status.set("Choose an object and a state first.")
            return
        self.goals = [g for g in self.goals if g[0] != obj] + [(obj, state)]
        self.make()

    def remove_goal(self):
        for i in reversed(self.goal_list.curselection()):
            del self.goals[i]
        self.make()

    def clear_goals(self):
        self.goals = []
        self.make()

    # --- plan ----------------------------------------------------------

    def make(self):
        self.stop()
        if not self.goals:
            self.plan, self.plan_stages = [], []
            self.status.set("Choose goals: use a preset, or pick an object and a state and click Add.")
        elif all(self.state[o] == s for o, s in self.goals):
            self.plan, self.plan_stages = [], []
            self.status.set("All goals are already reached.")
        else:
            steps = make_plan(self.actions, self.state, self.goals, self.done)
            if steps is None:
                self.plan, self.plan_stages = [], []
                self.status.set("No plan reaches these goals from here. Try other goals or Reset.")
            else:
                steps = by_stage(self.actions, self.state, steps)
                self.plan, self.plan_stages = steps, stages(self.actions, self.state, steps)
                crews = Counter(self.sector_of(k) for k in steps)
                self.status.set(
                    f"Plan: {len(steps)} steps in {max(self.plan_stages)} stages "
                    f"({', '.join(f'{s} {n}' for s, n in crews.items())}). "
                    "Click a step to see why it is needed. Step or Run carries it out.")
        self.refresh()

    def why(self, _event=None):
        selection = self.plan_list.curselection()
        if not selection:
            return
        i = selection[0]
        key = self.plan[i]
        made = {(obj, end) for obj, _, end in self.actions[key]["makes"]}
        reasons = [self.labels[k] for k in self.plan[i + 1:]
                   if made & set(conditions(self.actions[k]))]
        reasons += [f"goal {o} = {s}" for o, s in self.goals if (o, s) in made]
        self.status.set(f"Step {i + 1}, {self.labels[key]}, is needed for: "
                        + (", ".join(reasons) or "nothing left"))

    def step(self):
        remaining = [k for k in self.plan if k not in self.done]
        if not remaining:
            self.status.set("Make a plan first." if not self.plan else "The plan is done.")
            return False
        key = remaining[0]
        if self.unmet(key):
            self.status.set("The plan no longer fits the world. Change the goals or Reset.")
            return False
        self.do(key)
        if len(remaining) == 1:
            reached = all(self.state[o] == s for o, s in self.goals)
            self.status.set(f"Plan done in {len(self.plan)} steps. "
                            + ("All goals reached." if reached else "Some goals are not reached."))
            return False
        return True

    def run(self):
        self.stop()

        def tick():
            self.running = self.window.after(600, tick) if self.step() else None

        tick()

    def stop(self):
        if self.running:
            self.window.after_cancel(self.running)
            self.running = None

    def reset(self):
        self.stop()
        super().reset()
        self.make()

    # --- display -------------------------------------------------------

    def refresh(self):
        self.goal_list.delete(0, "end")
        for obj, state in self.goals:
            mark = "✓" if self.state[obj] == state else "·"
            self.goal_list.insert("end", f"{mark}  {obj} = {state}")
        self.plan_list.delete(0, "end")
        upcoming = next((i for i, k in enumerate(self.plan) if k not in self.done), None)
        for i, (key, stage) in enumerate(zip(self.plan, self.plan_stages)):
            mark = "✓" if key in self.done else "▶" if i == upcoming else " "
            self.plan_list.insert("end", f"{mark} {i + 1:2}. stage {stage}  {self.labels[key]}")
            if key in self.done:
                self.plan_list.itemconfig(i, fg="#2e7d32")
            elif i == upcoming:
                self.plan_list.itemconfig(i, bg="#fff3c4")
        if upcoming is not None:
            self.plan_list.see(upcoming)
        self.draw()


def main():
    window = tk.Tk()
    Planner(window)
    window.mainloop()


if __name__ == "__main__":
    main()
