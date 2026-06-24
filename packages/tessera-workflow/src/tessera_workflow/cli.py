from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console

console = Console()


def register(root_app: typer.Typer) -> None:
    app = typer.Typer(name="workflow", help="Validate Workflow Pack profile definitions.")
    root_app.add_typer(app)

    @app.command("validate")
    def validate_cmd(
        input: Path = typer.Option(..., "--input", "-i", help="Workflow YAML file or directory."),
        output: Path = typer.Option(Path("workflow_out"), "--output", "-o"),
    ) -> None:
        """Validate workflow pack governance definitions."""
        from tessera_core.models import RunContext
        from tessera_workflow.pack import WorkflowPack

        ctx = RunContext(job_name="workflow", output_dir=output)
        pack = WorkflowPack()
        artifacts = pack.run(input_path=input, ctx=ctx, options={})

        findings = ctx.metadata.get("findings", [])
        errors = [f for f in findings if f.severity == "error"]
        warnings = [f for f in findings if f.severity == "warning"]

        for art in artifacts:
            console.print(f"[green]wrote[/green] {art.path}")

        if errors:
            console.print(f"\n[red]{len(errors)} error(s)[/red], {len(warnings)} warning(s)")
            raise typer.Exit(1)
        console.print(f"\n[green]OK[/green] {len(warnings)} warning(s), 0 errors")
