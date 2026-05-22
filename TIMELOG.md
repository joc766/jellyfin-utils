# Time Log

| Date | Start | End | Duration | Project/Task | Notes |
|---|---:|---:|---:|---|---|
| 2026-05-03 | 12:30 PM | 2:00 PM | 1h 30 | python rip_disk MakeMKV progress parser | Parsed `PRGT` and `PRGC` lines using rich.text|
| 2026-05-04 | 9:00 AM | 10:00 AM | 1h | python rip_disk MakeMKV disc info parser | Add parsing title information from disc before ripping disc (WIP) |
| 2026-05-04 | 11:00 AM | 12:30 PM | 1h 30 | python rip_disk MakeMKV disc info parser | Complete parsing title, stream and disc info function, adjust cache size |
| 2026-05-04 | 2:00 PM | 4:15 PM | 2h 15 | refactoring rip_disk info parser | Complete `MakeMKVClient`, `MKVInfoParser` classes and write test case |
| 2026-04-09 | 9:00 AM | 12:00 PM | 3h 00 | initial bash tooling | First commit: `compress_mkv.sh`, `rip_disk.sh`, `sync-movie-to-server.sh` |
| 2026-04-13 | 10:00 AM | 10:45 AM | 45m | ffmpeg flags polish | Stereo audio mapping, metadata/chapters, subtitles off, faststart |
| 2026-04-13 | 11:00 AM | 11:15 AM | 15m | ffmpeg typo fix | Fixed `-sn` typo |
| 2026-04-15 | 2:00 PM | 3:00 PM | 1h 00 | compress script enhancement | Added optional destination parameter |
| 2026-04-16 | 9:30 AM | 9:45 AM | 15m | portability cleanup | Switched shebang to `/usr/bin/env bash` |
| 2026-04-17 | 10:00 AM | 10:15 AM | 15m | docs touch-up | Updated `compress_mkv` docstring |
| 2026-04-18 | 9:00 AM | 10:00 AM | 1h 00 | organize script + option fixes | Added `organize_files.sh`, fixed `-o` parsing |
| 2026-04-18 | 10:15 AM | 11:00 AM | 45m | orchestration wiring | Added `orchestrate.sh`, updated dependent scripts |
| 2026-04-18 | 11:15 AM | 11:30 AM | 15m | safety fix | Removed `eval` risk in sync orchestration |
| 2026-04-26 | 9:00 AM | 10:00 AM | 1h 00 | archive backups script | Added archive sync workflow |
| 2026-04-26 | 10:15 AM | 10:45 AM | 30m | network/perf tweaks | Private IP syncing + DVD option + timestamp/level fixes |
| 2026-04-28 | 1:00 PM | 1:30 PM | 30m | robustness update | Partial progress on pipefail/interrupt |
| 2026-04-30 | 9:00 AM | 10:00 AM | 1h 00 | TV workflow support | Added TV-specific script changes |
| 2026-05-05 | 9:00 AM | 12:30 PM | 3h 30 | parser/module refactor | Reorganized into modules, large parser/model/progress refactor |
| 2026-05-05 | 1:30 PM | 3:00 PM | 1h 30 | packaging + lint setup | Proper Python package structure, Ruff formatter, tests adjusted |
| 2026-05-06 | 9:00 AM | 12:00 PM | 3h 00 | ffmpeg compression v1 | First working `compress_mkv` client + progress parsing |
| 2026-05-06 | 1:00 PM | 3:30 PM | 2h 30 | ffmpeg hardening | Overwrite handling, ffprobe duration, interrupt handling |
| 2026-05-06 | 4:00 PM | 5:30 PM | 1h 30 | tests + sample data | Added progress/client tests and large fixture files |
| 2026-05-07 | 9:30 AM | 11:00 AM | 1h 30 | test reliability updates | Click exception tests, S3 fixture flow, parser renames |
| 2026-05-08 | 1:00 PM | 2:00 PM | 1h 00 | OMDb integration | Added `rename_movie` via OMDb API |
| 2026-05-09 | 9:30 AM | 10:45 AM | 1h 15 | organize/rip UX | Added `organize` command and rip confirmation UX |
| 2026-05-12 | 9:00 AM | 10:00 AM | 1h 00 | rsync interactive compare | Completed interactive rsync compare-before-sync |
| 2026-05-12 | 10:15 AM | 11:00 AM | 45m | repo restructuring | Moved bash scripts to `legacy/`, promoted `py/` to root |
| 2026-05-12 | 1:00 PM | 2:30 PM | 1h 30 | ffmpeg/rip polish | Deinterlace checks, inquirer updates, TODO scaffolding |
| 2026-05-13 | 9:00 AM | 10:00 AM | 1h 00 | organize enhancements | Interactive feature/extras/trailer selection + vi mode |
| 2026-05-13 | 10:15 AM | 10:45 AM | 30m | project maintenance | Dependency updates + `.gitignore` |
| 2026-05-14 | 2:00 PM | 2:15 PM | 15m | audio tweak | Stereo volume filter adjustment |
| 2026-05-15 | 9:00 AM | 11:00 AM | 2h 00 | rsync generalization | Bi-directional sync models/client + test updates |
| 2026-05-15 | 11:15 AM | 12:00 PM | 45m | OMDb error handling | Improved response validation and exception handling |
| 2026-05-17 | 10:00 AM | 11:30 AM | 1h 30 | rsync UX/debug | Verbose mode, merged stdout/stderr, direction/name improvements |
| 2026-05-17 | 11:45 AM | 12:15 PM | 30m | ffmpeg stream selection | English audio stream selection by tags |
| 2026-05-18 | 9:00 AM | 9:30 AM | 30m | backup audit utility | Added `find_missing_raw_movies` |
| 2026-05-19 | 9:00 AM | 12:30 PM | 3h 30 | rsync refactor (large) | Refactor around `AppConfig`, reusable paths, progress cleanup |
| 2026-05-21 | 9:00 AM | 10:45 AM | 1h 45 | config + context migration | `AppContext` in rip flow, env-file/default path wiring |
| 2026-05-21 | 11:00 AM | 12:30 PM | 1h 30 | missing-content commands | Added `find-missing-raw` and `find-missing-compressed` commands |
| 2026-05-21 | 1:30 PM | 2:30 PM | 1h 00 | OMDb/config cleanup | Moved OMDb key into config, prompt flow updates |
| 2026-05-22 | 9:00 AM | 10:30 AM | 1h 30 | compress config refactor | Wired config through compress flow; refactored ffmpeg paths/tests |
| 2026-05-22 | 10:45 AM | 11:30 AM | 45m | config tests + deps | Added config tests and dependency updates |
| 2026-05-22 | 11:30 AM | 12:15 PM | 45m | documentation | README refresh with command/option docs and startup steps |
|  |  |  | **45h 15m** | **Total** | **Rough estimate from commit size/scope** |
