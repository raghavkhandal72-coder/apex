"""
Apex Shell Completion Script Generator (Feature #86).
Generates native auto-completion scripts for Bash, Zsh, and PowerShell.
Zero external dependencies (pip = 0).
"""

from __future__ import annotations

from typing import Iterable


def generate_bash_completion(commands: Iterable[str]) -> str:
    cmds_str = " ".join(sorted(commands))
    return f"""# Apex Bash completion
_apex_completions() {{
    local cur="${{COMP_WORDS[COMP_CWORD]}}"
    local prev="${{COMP_WORDS[COMP_CWORD-1]}}"
    local commands="{cmds_str}"

    if [ "$COMP_CWORD" -eq 1 ]; then
        COMPREPLY=($(compgen -W "$commands" -- "$cur"))
    fi
}}
complete -F _apex_completions apex
complete -F _apex_completions python -m apex_council
"""


def generate_zsh_completion(commands: Iterable[str]) -> str:
    cmds_list = "\n        ".join([f"'{c}:{c} command'" for c in sorted(commands)])
    return f"""#compdef apex

_apex() {{
    local -a commands
    commands=(
        {cmds_list}
    )

    _arguments '1: :->command' '*: :->args'

    case $state in
        command)
            _describe -t commands 'apex command' commands
            ;;
    esac
}}

_apex "$@"
"""


def generate_powershell_completion(commands: Iterable[str]) -> str:
    cmds_quoted = ", ".join([f"'{c}'" for c in sorted(commands)])
    return f"""# Apex PowerShell argument completion
Register-ArgumentCompleter -Native -CommandName apex -ScriptBlock {{
    param($wordToComplete, $commandAst, $cursorPosition)
    $commands = @({cmds_quoted})
    $commands | Where-Object {{ $_ -like "$wordToComplete*" }} | ForEach-Object {{
        [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterValue', $_)
    }}
}}
"""


def generate_completion_script(shell: str, commands: Iterable[str]) -> str:
    shell = shell.lower().strip()
    if shell == "bash":
        return generate_bash_completion(commands)
    elif shell == "zsh":
        return generate_zsh_completion(commands)
    elif shell in ("powershell", "pwsh", "ps1"):
        return generate_powershell_completion(commands)
    else:
        return f"# Unsupported shell: {shell}. Supported: bash, zsh, powershell"
