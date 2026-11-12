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

text_board.txt holds the buttons. Every line is one row: a name, a colon and
the texts of the buttons with spaces between them, such as
  Blocks: Check Map Reduce Filter
Change that file to change the buttons; it is read when the program starts.

text_board_saved.txt holds the text and text_board_dataset.txt the dataset.
Both are saved after every change.

Uses only the standard library of Python (Tkinter is required for the window).
"""

import operator
import os
import tkinter as tk
from pathlib import Path

HERE = Path(__file__).parent
BUTTON_FILE = HERE / "text_board.txt"
TEXT_FILE = HERE / "text_board_saved.txt"
DATASET_FILE = HERE / "text_board_dataset.txt"
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


def run(text, data):
    """Work out every line of the text: a list of (line, answer, outcome), where the
    answer is True, False, None for a plain outcome or 'error'."""
    rows = data_rows(data)
    results = []
    for line in text.splitlines():
        if line.split():
            try:
                results.append((line.strip(), *run_line(line, rows)))
            except RunError as error:
                results.append((line.strip(), "error", str(error)))
    return results


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
        results = run(self.text.get("1.0", "end-1c"), self.dataset.get("1.0", "end-1c"))
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
