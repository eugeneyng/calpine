# TODO.MD

- [x] `[bug]` Saving an occurrence edit as "entire series" deletes the RRULE, because expanded occurrences report `frequency: "none"` so the Repeat dropdown is never set
- [ ] `[bug]` Clearing a series' repeat rule leaves its detached overrides (`RECURRENCE-ID`) behind as orphaned single events; decide whether to keep, convert, or warn instead of silently deleting them
- [ ] `[feature]` Support multiple WebDAV servers
- [ ] `[feature]` Login/logout functionality
