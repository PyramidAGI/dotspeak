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

## Planner

```
python homestead_planner.py
```

The planner uses the same two text files. You choose the goal and the
program works out the tasks.

- **Goals:** use a preset (**Everything** or one sector), or pick an object
  and a state, such as `roof = sealed`, and click **Add**.
- **Plan:** the planner works backward from each goal state. It finds a
  task that makes that state and plans that task's needs first. The plan
  only holds tasks that help reach the goals. For `roof = sealed` that is
  14 tasks, including the transport tasks that bring the stone.
- **Stages:** steps in the same stage do not depend on each other, so
  different crews could do them at the same time.
- **Why:** click a step to see which later step or goal needs it.
- **Step** does the next task, **Run** does the rest one by one, and
  **Reset** starts again. Changing the goals makes a new plan from the
  current state.

If the goals cannot all be true together, the planner says so. An example is
`cargo = secured` with `truck.position = site`: unloading at the site
removes the cargo.

## Web app planner

```
python webapp_planner.py
```

The same planner for another world: a web app with login. It works like
the homestead planner: choose goals or a preset, then Step or Run.

| File | What it holds |
| --- | --- |
| `webapp_tasks.txt` | The task list: auth, DB and UI sectors, ten tasks each |
| `webapp_world.txt` | The rules, in the same format as `homestead_world.txt` |
| `webapp_planner.py` | The planner with its own scene; the planning is shared with `homestead_planner.py` |

### Task form

Every task is exactly three words after `to-`: **verb + state + object**.
The object has the same name as in the world file, and the state is the
state the object is in before the task:

```
to-seed empty table
  needs: password = hashed
  makes: table: empty -> seeded
```

| Sector | Example tasks |
| --- | --- |
| Auth | `to-hash plain password`, `to-build missing endpoint`, `to-expire endless session` |
| DB | `to-install missing database`, `to-migrate empty schema`, `to-encrypt plain connection` |
| UI | `to-design missing layout`, `to-link unlinked form`, `to-fill empty dashboard` |

### How the sectors depend on each other

- Passwords are hashed before users are stored in the table.
- The login endpoint needs stored users and an encrypted connection.
- Sessions need the endpoint and a rotated secret.
- The login form is linked to the endpoint; the dashboard needs an
  expiring session and an indexed query.

So a UI goal pulls in DB and auth work. The goal `dashboard = filled`
gives a plan of 14 steps, from installing the database to filling the
dashboard. The UI preset needs 22 steps: 10 UI, 7 DB and 5 auth.

### Scene

The scene has one column per sector and one box per object. The colour
shows the state: red for the start state, yellow in between, green for the
last state. A thick border marks what the last task changed and a star
marks a goal. The drawing uses no task or object names, so it works with
any world file.

To plan another world, copy `webapp_planner.py` and change `task_file`,
`world_file` and `title`.

## Limits

The model has no amounts (how much stone), no time, no alternatives
(this *or* that), and no states that go back by themselves, such as a
window getting dirty again. Each task can be done once.
