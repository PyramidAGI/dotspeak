# homestead

Build a homestead by doing construction, transport and agriculture tasks
in the right order.

## Run

```
python homestead.py
```

Requires Python 3 with tkinter (included in the standard Windows installer).

## Files

| File | What it holds |
| --- | --- |
| `homestead.py` | The program: window, rules and drawing |
| `periodperiod.txt` | The task list: which tasks exist and in which sector |
| `homestead_world.txt` | The rules: objects, their states, and what each task needs and changes |

All three must be in the same folder. Both text files are read on start,
so restart the program after editing them.

## Playing

The scene is on the left and the task buttons are on the right, with one
tab per sector.

| Mark | Meaning |
| --- | --- |
| `▶` | Ready: click to do the task |
| `·` | Not ready yet: point at it to see what it needs |
| `✓` | Done |

The status line shows what each task needs, which task provides it,
and which tasks became possible after the last one.
**Hint** points to a ready task that helps other tasks forward.
**Reset** starts again. When all tasks are done, the homestead is complete.

## The task list: periodperiod.txt

A line ending in `sector` starts a sector, which becomes a tab. Every other
line is a task, which becomes a button:

```
construction sector
to_build empty ground
1. to-clean dirty window
```

A number at the start (`1.`) and the `to-` / `to_` prefix are ignored when
task names are matched against the world file. A task that is not in the
world file needs nothing and changes nothing.

## The rules: homestead_world.txt

The world is made of **objects** with **states**. Tasks are **actions**
that change those states.

### Objects

```
window: none, dirty, clean
wall.height: none, low, high
wall.surface: cracked, repaired
```

Each line names an object and its possible states. The first state is the
start state. Use `object.property` when one object has several properties.
Objects must be listed before the actions that use them.

### Actions

```
to_place new window
  needs: wall.height = high
  makes: window: none -> dirty

to-clean dirty window
  makes: window: dirty -> clean
```

- The first line is the task name, as in `periodperiod.txt`.
- `needs:` lists states that must be true before the task.
- `makes:` lists state changes. The object must be in the `from` state
  before the task, and is in the `to` state after it.
- Separate several items with commas. Lines starting with `#` are comments.

### Task order

The order of the tasks is not written anywhere. It follows from the states.
In the example above, *clean dirty window* can only happen after
*place new window*, because that is the task that makes a dirty window.

The scene draws the current state of each object, so the picture always
matches the world.

A misspelled object or state stops the program on start with the file name
and line number, for example:

```
homestead_world.txt line 3: unknown state window = claen
```

## Changing the world

- **New task:** add it to `periodperiod.txt` and add an action for it in
  `homestead_world.txt`.
- **Different order:** change the `needs:` and `makes:` lines. Make sure
  every state a task needs is made by some other task, or is a start state.
  If not, that task stays locked.
- **New object:** add it to the objects section. It changes the rules
  straight away. It only shows in the scene after drawing code is added for
  it in `homestead.py`.

## Limits

The model has no amounts (how much stone), no time, no alternatives
(this *or* that), and no states that go back by themselves, such as a
window getting dirty again. Each task can be done once.
