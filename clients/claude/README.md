# Claude Code projection

Canonical policy source: `skills/repo-learning/`.

Personal installation target: `$HOME/.claude/skills/repo-learning/`.

The installed directory must be a byte-for-byte projection of the canonical skill source; do not fork learning policy for Claude Code. Claude Code discovers custom Skills from `~/.claude/skills/` or project `.claude/skills/` directories.

For an enrolled repository, do not rely on Skill auto-discovery as the repository activation control plane. The repository's authoritative RepoLearn activation pointer must be projected into an instruction surface Claude Code actually loads (for example a thin `CLAUDE.md` pointer to the repository authority, when needed). That projection must only activate/reference canonical RepoLearn; it must not duplicate trigger, assessment, mastery, persistence, or cue-fading policy.

When the repository activation pointer is loaded, treat it as explicit activation and use the canonical `repo-learning` capability before substantive architecture guidance when available. Explicit manual Skill invocation remains valid. If the repository instruction pointer was not loaded, repository activation is not proven merely because the Skill is installed or auto-discovered.

Keep repository enrollment, repository-instruction loading, skill installation, skill loading, state loading, and actual learning interaction as separate evidence claims.
