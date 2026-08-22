<div align="center">

<img src="https://capsule-render.vercel.app/api?type=venom&height=170&color=0:0a1f14,60:0f3d26,100:00ff9c&text=stasis&fontSize=72&fontColor=e6fff2&fontAlignY=40&desc=a%20launcher%20that%20keeps%20the%20system%20out%20of%20the%20way&descAlignY=62&descSize=15&descColor=7ee2b0&animation=twinkling" width="100%" />

<img src="https://readme-typing-svg.demolab.com?font=Noto+Sans+Mono&weight=600&size=18&duration=2400&pause=700&color=00FF9C&center=true&vCenter=true&width=540&lines=click+an+app.;the+noise+freezes.;the+governor+flips.;you+play." alt="typing" />

<p>
<img src="https://img.shields.io/badge/python-3.11%2B-00b85c?style=flat-square" alt="python" />
<img src="https://img.shields.io/badge/dependencies-zero-00ff9c?style=flat-square" alt="zero deps" />
<img src="https://github.com/lonexasss/stasis/actions/workflows/ci.yml/badge.svg?style=flat-square" alt="ci status" />
<img src="https://img.shields.io/badge/license-MIT-0f3d26?style=flat-square" alt="mit" />
</p>

</div>

`stasis` launches applications inside resource-controlled scopes and puts
the rest of the desktop on hold while they run. No magic, no ram cleaners —
only mechanisms the kernel actually provides: systemd scopes, cgroup limits,
SIGSTOP, cpufreq governors.

```text
             ┌──────────────────────────────┐
  click  ──▶ │  systemd-run --user --scope  │
             │    AllowedCPUs · MemoryHigh  │
             └──────────────┬───────────────┘
                            ▼
     SIGSTOP ──▶ firefox · discord · telegram
                            ▼
                governor → performance
                            ▼
              app exits → everything back
```

## mechanics

| feature | mechanism |
|---|---|
| cpu affinity per app | `AllowedCPUs=` scope property — pin a game to P-cores, trap the rest elsewhere |
| memory ceilings | `MemoryHigh=` / `MemoryMax=` — an app that leaks stops at the fence instead of taking the system down |
| background freeze | `SIGSTOP` to everything matching your `freeze` list, `SIGCONT` on exit |
| cold page reclaim | write into the frozen apps' `memory.reclaim` — kernel picks truly cold pages, nothing is destroyed |
| governor switch | `performance` while the app runs, original state restored afterwards |

## what stasis will never do

- "free up ram" by dropping disk caches — that cache exists to make things faster
- raise arbitrary processes to realtime priority — that is how audio servers die
- pretend `EmptyWorkingSet`-style tricks help anything

## usage

```console
$ stasis run game -- steam            # apply profile, launch inside scope
$ stasis run game --dry-run -- steam  # show planned actions only
$ stasis freeze discord               # manual SIGSTOP by pattern
$ stasis thaw                         # resume everything stasis froze
$ stasis trim <pid>                   # reclaim cold pages of one process
$ stasis status                       # what is frozen right now
$ stasis profiles                     # list configured profiles
```

## profiles

`~/.config/stasis/config.toml`

```toml
[game]
cpu_affinity = "0-7"        # app lives here
memory_high = "8G"
memory_max = "12G"
governor = "performance"
freeze = ["firefox", "telegram"]
trim_frozen = true

[idle]
# a profile may also just be a fence:
memory_max = "2G"

[by_category]
Game = "game"               # apps in this category launch with this profile
```

Desktop-critical processes (pipewire, compositor, dbus...) are always
protected from freezing via a built-in ignore list.

## install

download `stasis-gui` from
[releases](https://github.com/lonexasss/stasis/releases), unpack next to
`install.sh`, run it once:

```console
$ ./install.sh
```

`Stasis` appears in the applications menu. no config needed — a default
one is created on first launch. games get the game profile automatically.

## gui

```console
$ stasis-gui
```

a grid of every installed application, like a phone home screen.
click an app: it launches inside its scope, background noise freezes,
the governor flips to performance and back when the app closes.
search field up top, manual freeze/thaw on the right.
still zero dependencies beyond the stdlib.

<!-- screenshot slot:
![gui](docs/gui.png)
-->

## requirements

- linux with systemd and cgroup v2
- root only where the kernel demands it: governor switching, trimming
  non-delegated cgroups
- python >= 3.11, zero runtime dependencies

## development

```console
$ pip install -e .[dev]
$ pytest
```

<div align="center">

### the pet

it eats contributions. feed the repo.

<img src="https://raw.githubusercontent.com/lonexasss/stasis/output/snake.svg" width="100%" alt="snake" />

<img src="https://capsule-render.vercel.app/api?type=waving&height=80&color=100:0a1f14,50:0f3d26,0:00ff9c&section=footer&animation=twinkling" width="100%" />

</div>
