"""dotspeak: build a sentence by typing number codes and picking words.

Keys:
  1 go, 2 plus, 3 minus, 4 home, 5 stat, 6 pref, 7 time, 8 tool
    Each digit extends the current code. The word list shown is the file
    named after the code, e.g. 7 -> time.txt, 7 7 -> timetime.txt,
    7 5 -> timestat.txt.
  Up / Down   move through the list
  + / -       move down / up in the list
  Enter       add the selected word to the sentence
  Escape      cancel the current code
  Backspace   remove the last digit of the code, or the last word
  Delete      clear the sentence

On start, hometool.txt is copied over toolhome.txt.
"""

import shutil
import tkinter as tk
from pathlib import Path

BASE_DIR = Path(__file__).parent

NAMES = {
    "1": "go",
    "2": "plus",
    "3": "minus",
    "4": "home",
    "5": "stat",
    "6": "pref",
    "7": "time",
    "8": "tool",
}

FONT = ("Segoe UI", 12)


def list_file(code):
    return BASE_DIR / ("".join(NAMES[d] for d in code) + ".txt")


def load_words(path):
    if not path.exists():
        return None
    text = path.read_text(encoding="utf-8")
    return [line.strip() for line in text.splitlines() if line.strip()]


class App:
    def __init__(self, root):
        self.root = root
        self.code = ""
        self.words = []

        root.title("dotspeak")
        root.geometry("640x420")

        self.sentence = tk.Entry(root, font=FONT, state="readonly",
                                 readonlybackground="white")
        self.sentence.pack(fill="x", padx=10, pady=(10, 4))

        self.status = tk.Label(root, font=FONT, anchor="w")
        self.status.pack(fill="x", padx=10)

        self.listbox = tk.Listbox(root, font=FONT, activestyle="none",
                                  exportselection=False, takefocus=0)
        self.listbox.pack(fill="both", expand=True, padx=10, pady=(4, 10))
        self.listbox.bind("<ButtonRelease-1>", lambda e: self.pick())
        self.listbox.bind("<Double-Button-1>", lambda e: self.pick())

        root.bind("<Key>", self.on_key)
        root.bind("<Down>", lambda e: self.move(1))
        root.bind("<Up>", lambda e: self.move(-1))
        root.bind("<Return>", lambda e: self.pick())
        root.bind("<KP_Enter>", lambda e: self.pick())
        root.bind("<Escape>", lambda e: self.reset_code())
        root.bind("<BackSpace>", lambda e: self.backspace())
        root.bind("<Delete>", lambda e: self.set_sentence(""))

        root.focus_force()
        self.refresh()

    # --- sentence -------------------------------------------------------

    def get_sentence(self):
        return self.sentence.get()

    def set_sentence(self, text):
        self.sentence.config(state="normal")
        self.sentence.delete(0, "end")
        self.sentence.insert(0, text)
        self.sentence.config(state="readonly")

    # --- code / list ----------------------------------------------------

    def on_key(self, event):
        if event.char in NAMES:
            self.code += event.char
            self.refresh()
        elif event.char == "+":
            self.move(1)
        elif event.char == "-":
            self.move(-1)

    def backspace(self):
        if self.code:
            self.code = self.code[:-1]
            self.refresh()
        else:
            self.set_sentence(" ".join(self.get_sentence().split()[:-1]))

    def reset_code(self):
        self.code = ""
        self.refresh()

    def refresh(self):
        self.listbox.delete(0, "end")
        self.words = []

        if not self.code:
            self.status.config(text="Type 1-8: " + ", ".join(
                f"{d}={n}" for d, n in NAMES.items()))
            return

        path = list_file(self.code)
        words = load_words(path)
        codes = " ".join(self.code)
        if words is None:
            self.status.config(text=f"{codes}  ->  {path.name} (not found)")
            return
        if not words:
            self.status.config(text=f"{codes}  ->  {path.name} (empty)")
            return

        self.status.config(text=f"{codes}  ->  {path.name}")
        self.words = words
        for word in words:
            self.listbox.insert("end", word)
        self.select(0)

    def select(self, index):
        self.listbox.selection_clear(0, "end")
        self.listbox.selection_set(index)
        self.listbox.activate(index)
        self.listbox.see(index)

    def move(self, step):
        if not self.words:
            return
        current = self.listbox.curselection()
        index = current[0] + step if current else 0
        self.select(max(0, min(index, len(self.words) - 1)))

    def pick(self):
        current = self.listbox.curselection()
        if not current:
            return
        word = self.words[current[0]]
        sentence = self.get_sentence()
        self.set_sentence(f"{sentence} {word}" if sentence else word)
        self.reset_code()


def main():
    source = BASE_DIR / "hometool.txt"
    if source.exists():
        shutil.copyfile(source, BASE_DIR / "toolhome.txt")

    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
