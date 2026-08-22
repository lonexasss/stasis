<div align="center">

<img src="https://capsule-render.vercel.app/api?type=venom&height=160&color=0:0a0a0a,100:3a3a3a&text=stasis&fontSize=70&fontColor=e6e6e6&fontAlignY=40&desc=a%20launcher%20that%20keeps%20the%20system%20out%20of%20the%20way&descAlignY=62&descSize=15&descColor=a8a8a8&animation=twinkling" width="100%" />

<img src="https://github.com/lonexasss/stasis/actions/workflows/ci.yml/badge.svg?style=flat-square" alt="ci status" />

</div>

`stasis` launches applications inside resource-controlled scopes and puts
the rest of the desktop on hold while they run. No magic, no ram cleaners —
only mechanisms the kernel actually provides: systemd scopes, cgroup limits,
SIGSTOP, cpufreq governors.

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
$ stasis run game -- steam          # apply profile, launch inside scope
$ stasis run game --dry-run -- steam  # show planned actions only
$ stasis freeze discord             # manual SIGSTOP by pattern
$ stasis thaw                       # resume everything stasis froze
$ stasis trim <pid>                 # reclaim cold pages of one process
$ stasis status                     # what is frozen right now
$ stasis profiles                   # list configured profiles
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
```

Desktop-critical processes (pipewire, compositor, dbus...) are always
protected from freezing via a built-in ignore list.

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

<img src="https://capsule-render.vercel.app/api?type=waving&height=80&color=0:0a0a0a,100:3a3a3a&section=footer&animation=waving" width="100%" />

</div>
