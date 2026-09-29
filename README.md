# dotspeak

Build a sentence by typing number codes and picking words from lists.

## Run

```
python app.py
```

Requires Python 3 with tkinter (included in the standard Windows installer).

## Keys

| Key | Action |
| --- | --- |
| `1`–`8` | Extend the current code and show its word list |
| `↓` / `↑` | Move through the list |
| `Enter` | Add the selected word to the sentence (clicking works too) |
| `Esc` | Cancel the current code |
| `Backspace` | Remove the last digit of the code, or the last word of the sentence |
| `Delete` | Clear the sentence |

## Codes and word files

Each digit maps to a name:

| Digit | Name |
| --- | --- |
| 1 | go |
| 2 | plus |
| 3 | minus |
| 4 | home |
| 5 | stat |
| 6 | pref |
| 7 | time |
| 8 | tool |

The word list for a code is the file named after the concatenated names,
next to `app.py`:

- `7` → `time.txt`
- `7 7` → `timetime.txt`
- `7 5` → `timestat.txt`
- `4 4` → `homehome.txt`

Word files contain one word per line. They are re-read on every keypress,
so edits show up without restarting. A missing file is reported in the
status line.

To rename the digits, edit the `NAMES` table at the top of `app.py`.

## Counting entries

```
python count.py
```

Prints the number of entries in each word file and the total. It counts
non-empty lines in every `.txt` file next to `app.py`.
