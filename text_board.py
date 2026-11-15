"""Write text on a board by clicking buttons, next to a board for the dataset.
Run: python text_board.py

There are two boards: Text on the left and Dataset on the right, for the data
the text is about. Click in a board to work in it; its border turns blue. Drag
the bar between the boards to give one of them more room.

Every button adds its text at the cursor of that board, with a space between
the texts. Click in the text to move the cursor, so a button can also add its
text in the middle. You can type, select and delete as well; a button replaces
the selected text.

  Newline   starts a new line at the cursor
  Undo      takes back the last change in that board, also a Clear (Ctrl+Z does
            the same, Ctrl+Y brings the change back)
  Clear     wipes that board; the other board stays as it is

Run (or F5) works out every line of the text against the dataset and shows the
outcome per line in the Result board at the bottom.

Help (or F1) shows the file 'A program basically is an energy landscape.txt' in
a window of its own. Change that file to change the help.

In the dataset every line is one row of words, such as
  john social pref amsterdam
  jill social stat emo 30
Every word of a row that is a number counts as a number of that row.

A line of the text picks rows and says what to do with them:
  john              a word picks the rows that hold that word; capitals do not
                    matter, so Physics picks the rows with physics
  john pref         two words pick the rows that hold both
  economics or physics      or picks the rows that hold either
  not pref          not picks the rows without the word
  Dataset           every row; with other words it can be left out
  Head 2            only the first 2 of the picked rows; Head alone is the first
  Tail 2            only the last 2 of the picked rows; Tail alone is the last
  Count             how many rows are picked
  sum avg min max   over all the numbers in the picked rows; sum alone adds up
                    every number in the dataset
  = > <             compares the outcome with the number that follows
  Check             at the start of the line: answers yes or no. With = > or <
                    it is yes when the comparison holds, without them it is yes
                    when at least one row is picked.
So 'Check Count Dataset = 2' answers yes for the two rows above,
'avg stat' gives 30 and 'Tail social' shows the row of jill. Run does not know
the other operators and blocks yet and says so on their lines.

Lkpadd looks answers up in the dataset and asks for the ones that are missing:
  Def Function():
      Lkpadd Physics loc Ctrl X
asks 'For Function, what is the physics.loc.control.X?' and adds your answer to
the dataset as the row 'Function physics loc control X' and the answer. The next
Run finds that row and does not ask again.
  Def name():       names what the indented lines below it are about
  Lkpadd            the questions come from convolute.txt: one word from each of
                    its lines. Every word you leave out stands for all the words
                    of its line, so 'Lkpadd Physics' stands for a set of 48
                    physics questions. Ctrl and Nav stand for control and
                    navigate.
  3 at most         a Lkpadd line asks at most 3 questions in a Run, taken at
                    random from the ones of its set that are not in the dataset
                    yet. The dialog says so: 'This is question 1 of 3, taken at
                    random out of a set of 48 questions.' Run again for 3 more.
  Lkpadd Economics pump     another word is what the question is about: 'For
                    pump, what is the ...?'. Without it and without a Def the
                    question is about 'this function'.
An empty answer skips a question; Cancel stops the asking for this Run.

text_board.txt holds the buttons. Every line is one row: a name, a colon and
the texts of the buttons with spaces between them, such as
  Blocks: Check Map Reduce Filter
Change that file to change the buttons; it is read when the program starts.

text_board_saved.txt holds the text and text_board_dataset.txt the dataset.
Both are saved after every change.

Uses only the standard library of Python (Tkinter is required for the window).
"""

import itertools
import operator
import os
import random
import tkinter as tk
from pathlib import Path
from tkinter import simpledialog

HERE = Path(__file__).parent
BUTTON_FILE = HERE / "text_board.txt"
TEXT_FILE = HERE / "text_board_saved.txt"
DATASET_FILE = HERE / "text_board_dataset.txt"
CONVOLUTE_FILE = HERE / "convolute.txt"
HELP_FILE = HERE / "A program basically is an energy landscape.txt"
ACTIVE = "#2f5bd3"  # Border of the board the buttons work in.
FONT = ("Segoe UI", 11)
BUTTON_FONT = ("Consolas", 12, "bold")
TEXT_FONT = ("Consolas", 13)
PER_LINE = 12  # A row with more buttons than this goes on over the next line.
# (fill, text colour) of the buttons of the first row, the second row and so on.
ROW_COLORS = (("#cfe3f7", "#1f4f86"), ("#e2d6f3", "#4c2f91"), ("#fbe9b7", "#6f560a"),
              ("#d3edd5", "#1f5c23"), ("#fbd9bb", "#7a4210"), ("#d5ecec", "#1d5a5a"))


def load_rows(path=BUTTON_FILE):
    """The rows of buttons: a list of (name, texts). A line without a colon has no name."""
    rows = []
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            name, colon, texts = line.partition(":")
            if not colon:
                name, texts = "", line
            if texts.split():
                rows.append((name.strip(), texts.split()))
    return rows


class RunError(Exception):
    """A line of the text that Run cannot work out."""


MEASURES = {"sum": sum, "avg": lambda values: sum(values) / len(values), "min": min,
            "max": max}
COMPARE = {"=": operator.eq, ">": operator.gt, "<": operator.lt}
NOT_YET = {"+", "-", "*", "/", "sin", "cos", "sqrt", "map", "reduce", "filter", "estimate",
           "compute"}
# Colour of a line in the Result board: for yes, for no, for a plain outcome, for an error.
RESULT_COLORS = {True: "#1f5c23", False: "#b03a2e", None: "#222222", "error": "#a05a00"}


def number(word):
    try:
        return float(word)
    except ValueError:
        return None


def show(value):
    return f"{value:.12g}"


def data_rows(text):
    """The rows of the dataset: the words of every line that has any."""
    return [line.split() for line in text.splitlines() if line.split()]


def run_line(line, rows):
    """Work out one line of the text against the rows of the dataset.
    Gives (answer, outcome): the answer is True or False for a yes or no, else None."""
    words = line.split()
    check = words[0].lower() == "check"
    if check:
        words = words[1:]
    sign = next((word for word in words if word in COMPARE), None)
    target = None
    if sign:
        at = words.index(sign)
        target = number(words[at + 1]) if len(words) == at + 2 else None
        if target is None:
            raise RunError(f"{sign} needs one number after it")
        words = words[:at]

    take = None  # ('head' or 'tail', how many): the part of the picked rows to keep.
    others = []
    at = 0
    while at < len(words):
        low = words[at].lower()
        if low in ("head", "tail"):
            if take:
                raise RunError("a line can have only one Head or Tail")
            many = number(words[at + 1]) if at + 1 < len(words) else None
            if many is None:
                many = 1
            else:
                at += 1
            if many < 1 or many != int(many):
                raise RunError(f"{low.capitalize()} needs a whole number of rows, 1 or more")
            take = (low, int(many))
        else:
            others.append(words[at])
        at += 1
    words = others

    measure = None
    groups = [[]]  # The row must hold every word of one of the groups; 'or' starts a group.
    negate = False
    for word in words:
        low = word.lower()
        if low in NOT_YET:
            raise RunError(f"Run does not know {word} yet")
        if low == "count" or low in MEASURES:
            if measure:
                raise RunError(f"{measure} and {low} cannot both be worked out in one line")
            measure = low
        elif low == "or":
            groups.append([])
        elif low == "not":
            negate = True
        elif low not in ("dataset", "and"):
            groups[-1].append((low, negate))
            negate = False
    if negate:
        raise RunError("not needs a word after it")

    def picked(row):
        have = {word.lower() for word in row}
        return any(all((word in have) != without for word, without in group)
                   for group in groups)

    found = [row for row in rows if picked(row)]
    if take:
        found = found[:take[1]] if take[0] == "head" else found[-take[1]:]
    if measure in MEASURES:
        values = [number(word) for row in found for word in row if number(word) is not None]
        if not values:
            raise RunError(f"{measure} finds no numbers in the rows it picked")
        value = MEASURES[measure](values)
        outcome = f"{measure} is {show(value)}"
    else:
        value = len(found)
        outcome = f"{value} row{'' if value == 1 else 's'}"
        if found and measure is None:
            outcome += ": " + "; ".join(" ".join(row) for row in found[:3])
            outcome += "; ..." if len(found) > 3 else ""
    if sign:
        answer = COMPARE[sign](value, target)
    elif check and measure:
        raise RunError(f"Check {measure} needs = > or < and a number")
    else:
        answer = bool(found) if check else None
    return answer, outcome


ALIASES = {"ctrl": "control", "nav": "navigate"}  # Buttons that stand for a question word.
MAX_ASK = 3  # The most questions one Lkpadd line asks in a Run.


def load_levels(path=CONVOLUTE_FILE):
    """The words of each level of a question: one list per line that is not empty."""
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8").splitlines()
    return [line.split() for line in lines if line.split()]


def lookup_add(words, name, rows, levels, ask):
    """Look up the answers to the questions these words stand for, and ask for the
    missing ones. New answers are added to the rows. Gives (outcome, added rows)."""
    if not levels:
        raise RunError(f"Lkpadd finds no questions in {CONVOLUTE_FILE.name}")
    chosen = [[] for _ in levels]
    subject = []
    for word in words:
        low = ALIASES.get(word.lower(), word.lower())
        for level, picks in zip(levels, chosen):
            match = next((known for known in level if known.lower() == low), None)
            if match:
                if match not in picks:
                    picks.append(match)
                break
        else:
            subject.append(word)
    if not subject and name:
        subject = [name]
    whom = " ".join(subject) or "this function"
    subject = subject or ["function"]
    keys = list(itertools.product(*(picks or level for picks, level in zip(chosen, levels))))
    still_open = []
    for key in keys:
        start = [word.lower() for word in subject + list(key)]
        if not any([word.lower() for word in row[:len(start)]] == start for row in rows):
            still_open.append(key)
    known = len(keys) - len(still_open)
    # At most MAX_ASK questions per line: a random choice from the open ones.
    asking = sorted(random.sample(still_open, min(MAX_ASK, len(still_open))), key=keys.index)
    added = []
    for at, key in enumerate(asking, 1):
        note = f"This is question {at} of {len(asking)}"
        note += (f", taken at random out of a set of {len(keys)} questions."
                 if len(keys) > len(asking) else ".")
        if known:
            note += f" {known} of that set are already in the dataset."
        answer = ask(f"For {whom}, what is the {'.'.join(key)}?\n\n{note}") if ask else None
        if answer and answer.split():
            added.append(subject + list(key) + answer.split())
            rows.append(added[-1])
    outcome = (f"{whom}: asked {len(asking)} out of a set of {len(keys)}, {len(added)} added, "
               f"{known} already in the dataset, {len(still_open) - len(added)} still open")
    return outcome, added


def run(text, data, ask=None):
    """Work out every line of the text. Gives (results, added): the results are a list
    of (line, answer, outcome), where the answer is True, False, None for a plain
    outcome or 'error'; added are the rows Lkpadd made for the dataset.
    ask(question) gives the answer to a question of Lkpadd, '' to skip it or None to
    stop asking."""
    rows = data_rows(data)
    levels = load_levels()
    results, added = [], []
    name = None  # What the lines are about: the name of the Def they stand under.
    stopped = False

    def ask_on(question):
        nonlocal stopped
        answer = None if stopped or not ask else ask(question)
        stopped = answer is None
        return answer

    for line in text.splitlines():
        words = line.split()
        if not words:
            continue
        if not line[0].isspace():
            name = None
        try:
            first = words[0].lower()
            if first == "def":
                name = words[1].split("(")[0].rstrip(":") if len(words) > 1 else ""
                if not name:
                    raise RunError("Def needs a name, such as Def Function():")
                results.append((line.strip(), None, f"the lines below are about {name}"))
            elif first == "lkpadd":
                outcome, new = lookup_add(words[1:], name, rows, levels, ask_on)
                added += new
                results.append((line.strip(), None, outcome))
            else:
                results.append((line.strip(), *run_line(line, rows)))
        except RunError as error:
            results.append((line.strip(), "error", str(error)))
    return results, added


class TextBoard:
    def __init__(self, root, button_file=BUTTON_FILE, text_file=TEXT_FILE,
                 dataset_file=DATASET_FILE):
        self.root = root
        self.files = {}  # board: the file it is saved in
        self.names = {}  # board: its name
        root.title("Text board")
        root.geometry("1100x760")

        top = tk.Frame(root)
        top.pack(fill="x", padx=10, pady=(10, 6))
        for name, command in (("Newline", self.newline), ("Undo", self.undo),
                              ("Clear", self.clear)):
            tk.Button(top, text=name, font=FONT, width=8, takefocus=False,
                      command=command).pack(side="left", padx=(0, 4))
        tk.Button(top, text="Run", font=FONT, width=8, takefocus=False, bg="#d3edd5",
                  activebackground="#d3edd5", command=self.run).pack(side="left", padx=(12, 0))
        root.bind("<F5>", lambda event: self.run())
        tk.Button(top, text="Help", font=FONT, width=8, takefocus=False,
                  command=self.help).pack(side="left", padx=(12, 0))
        root.bind("<F1>", lambda event: self.help())
        self.help_window = None

        rows = load_rows(button_file)
        palette = tk.Frame(root)
        palette.pack(fill="x", padx=10)
        line = 0
        for number, (name, texts) in enumerate(rows):
            fill, ink = ROW_COLORS[number % len(ROW_COLORS)]
            tk.Label(palette, text=name, font=FONT, anchor="w").grid(
                row=line, column=0, sticky="w", padx=(0, 8))
            for index, text in enumerate(texts):
                tk.Button(palette, text=text, font=BUTTON_FONT, bg=fill, fg=ink,
                          activebackground=fill, takefocus=False,
                          command=lambda t=text: self.add(t)).grid(
                              row=line + index // PER_LINE, column=1 + index % PER_LINE,
                              sticky="ew", padx=2, pady=2)
            line += (len(texts) - 1) // PER_LINE + 1

        self.status = tk.Label(root, font=FONT, anchor="w", fg="#555")
        self.status.pack(side="bottom", fill="x", padx=10, pady=(4, 8))

        self.result_name = tk.Label(root, text="Result", font=FONT, anchor="w", fg="#555")
        self.result = tk.Text(root, font=TEXT_FONT, wrap="word", height=6, bg="#f0f0f0",
                              relief="flat", padx=10, pady=6, state="disabled",
                              highlightthickness=2, highlightbackground="#cccccc")
        for answer, color in RESULT_COLORS.items():
            self.result.tag_config(str(answer), foreground=color)
        self.result.pack(side="bottom", fill="x", padx=10)  # Above the status line.
        self.result_name.pack(side="bottom", fill="x", padx=10, pady=(6, 0))

        boards = tk.PanedWindow(root, orient="horizontal", sashwidth=8, borderwidth=0)
        boards.pack(fill="both", expand=True, padx=10, pady=(8, 0))
        self.active = None  # The board the buttons work in: the one clicked in last.
        self.text = self.active = self.board(boards, "Text", text_file, 650)
        self.dataset = self.board(boards, "Dataset", dataset_file, 350)
        self.text.focus_set()
        self.say("Click a button to add its text at the cursor." if rows
                 else f"{button_file.name} has no buttons: add a line such as "
                      "'Blocks: Check Map Filter'.")

    def board(self, boards, name, file, width):
        """Add a board to the window: a text you can type in, loaded from its file."""
        holder = tk.Frame(boards)
        tk.Label(holder, text=name, font=FONT, anchor="w", fg="#555").pack(fill="x")
        board = tk.Text(holder, font=TEXT_FONT, wrap="word", undo=True, bg="#f7f7fb",
                        relief="flat", padx=10, pady=8, insertwidth=2, spacing1=2,
                        spacing3=2, width=1, highlightthickness=2,
                        highlightbackground="#cccccc", highlightcolor=ACTIVE)
        bar = tk.Scrollbar(holder, command=board.yview)
        board.config(yscrollcommand=bar.set)
        bar.pack(side="right", fill="y")
        board.pack(side="left", fill="both", expand=True)
        boards.add(holder, width=width, minsize=150, stretch="always")
        self.files[board], self.names[board] = file, name
        if file.exists():
            board.insert("1.0", file.read_text(encoding="utf-8"))
        board.edit_reset()
        board.edit_modified(False)
        board.bind("<<Modified>>", lambda event: self.changed(board))
        board.bind("<FocusIn>", lambda event: self.work_in(board))
        board.mark_set("insert", "end")
        return board

    def work_in(self, board):
        """Let the buttons work in this board from now on."""
        self.active = board

    def run(self):
        """Work out the text against the dataset and show the outcome of every line."""
        results, added = run(self.text.get("1.0", "end-1c"),
                             self.dataset.get("1.0", "end-1c"), self.ask)
        if added:  # The answers Lkpadd got: new rows at the end of the dataset.
            data = self.dataset
            data.edit_separator()
            if data.get("1.0", "end-1c") and data.get("end-2c", "end-1c") != "\n":
                data.insert("end", "\n")
            data.insert("end", "".join(" ".join(row) + "\n" for row in added))
            data.edit_separator()
            data.see("end")
            self.changed(data)
        self.result.config(state="normal")
        self.result.delete("1.0", "end")
        for line, answer, outcome in results:
            word = {True: "yes: ", False: "no: "}.get(answer, "")
            self.result.insert("end", f"{line}   ->   {word}{outcome}\n", str(answer))
        if not results:
            self.result.insert("end", "The text has no lines to run.")
        self.result.config(state="disabled")
        self.result_name.config(text="Result")
        self.active.focus_set()

    def help(self):
        """Show the help file in a window of its own; it is read on every click."""
        if not HELP_FILE.exists():
            self.say(f"There is no help file: {HELP_FILE.name} is missing.")
            return
        if self.help_window and self.help_window.winfo_exists():
            self.help_window.destroy()
        self.help_window = window = tk.Toplevel(self.root)
        window.title("Help")
        window.geometry("560x320")
        text = tk.Text(window, font=FONT, wrap="word", relief="flat", padx=14, pady=12,
                       spacing2=3)
        bar = tk.Scrollbar(window, command=text.yview)
        text.config(yscrollcommand=bar.set)
        bar.pack(side="right", fill="y")
        text.pack(side="left", fill="both", expand=True)
        text.insert("1.0", HELP_FILE.read_text(encoding="utf-8", errors="replace"))
        text.config(state="disabled")
        window.bind("<Escape>", lambda event: window.destroy())

    def ask(self, question):
        """Ask a question of Lkpadd: the answer, '' to skip it or None to stop asking."""
        return simpledialog.askstring(
            "Lkpadd", question + "\n\nAn empty answer skips this question; Cancel stops.",
            parent=self.root)

    def say(self, text):
        self.status.config(text=text)

    def add(self, word):
        """Put the text of a button at the cursor, with a space to the texts around it."""
        text = self.active
        text.edit_separator()
        if text.tag_ranges("sel"):
            text.delete("sel.first", "sel.last")
        before = text.get("insert -1c", "insert") if text.compare("insert", ">", "1.0") else ""
        after = text.get("insert", "insert +1c")
        text.insert("insert", (" " if before and not before.isspace() else "") + word
                    + (" " if after and not after.isspace() else ""))
        self.finish()

    def newline(self):
        self.active.edit_separator()
        self.active.insert("insert", "\n")
        self.finish()

    def clear(self):
        self.active.edit_separator()
        self.active.delete("1.0", "end")
        self.finish()
        name = self.names[self.active]  # After the save has reported, so this shows.
        self.root.after_idle(lambda: self.say(f"{name} wiped. Undo brings it back."))

    def undo(self):
        try:
            self.active.edit_undo()
        except tk.TclError:
            self.say(f"Nothing to undo in {self.names[self.active]}.")
        self.finish()

    def finish(self):
        """Close a change: one step for Undo, the cursor in sight and ready for typing."""
        self.active.edit_separator()
        self.active.see("insert")
        self.active.focus_set()

    def changed(self, board):
        """Save a board after every change to it."""
        if board.edit_modified():
            file = self.files[board]
            temporary = file.with_suffix(".tmp")
            temporary.write_text(board.get("1.0", "end-1c"), encoding="utf-8")
            os.replace(temporary, file)
            board.edit_modified(False)
            self.say(f"{self.names[board]} saved in {file.name}.")
            if self.result.get("1.0", "end-1c"):
                self.result_name.config(text="Result of the last Run; changed since")


def main():
    window = tk.Tk()
    TextBoard(window)
    window.mainloop()


if __name__ == "__main__":
    main()
