# Codex projection

Canonical policy source: `skills/repo-learning/`.

Personal installation target: `${CODEX_HOME:-$HOME/.codex}/skills/repo-learning/`.

The installed directory must be a byte-for-byte projection of the canonical skill source; do not fork `SKILL.md` policy for Codex.

For an enrolled repository, do not rely on Codex Skill auto-discovery as the repository activation control plane. The repository's loaded instruction surface (normally its authoritative `AGENTS.md` or a thin client projection of it) must carry the RepoLearn activation pointer. When that pointer is loaded, treat it as explicit activation and use the canonical `repo-learning` capability before substantive architecture guidance when available.

`$repo-learning` remains a valid explicit manual control. If the repository instruction pointer was not loaded, repository activation is not proven even if the Skill is installed or appears in the session inventory.

Keep these claims separate: repository enrollment, repository-instruction loading, skill installation, skill loading, state loading, and actual learning interaction.
