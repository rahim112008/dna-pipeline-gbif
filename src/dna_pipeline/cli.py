import typer
from .ingest import load_data
from .transform import map_to_dwc
from .validate import validate_dwc, validate_mixs_terms
from .publish import generate_dwca

app = typer.Typer()


@app.command()
def run(input_path: str, output_dir: str = "data/output"):
    typer.echo(f"📥 Chargement de {input_path}...")
    df = load_data(input_path)
    typer.echo("🔄 Mapping vers Darwin Core + MIxS...")
    df_mapped = map_to_dwc(df)
    typer.echo("✅ Validation métier...")
    report = validate_dwc(df_mapped)
    if report["errors"]:
        for e in report["errors"]:
            typer.echo(f"❌ {e['type']}: {e['message']}", err=True)
        raise typer.Exit(code=1)
    for w in report["warnings"]:
        typer.echo(f"⚠️  {w['type']}: {w['message']}")
    typer.echo("🔍 Validation MIxS...")
    mixs = validate_mixs_terms(df_mapped)
    if not mixs["valid"]:
        typer.echo(f"⚠️  Termes MIxS invalides : {mixs['invalid_terms']}")
    typer.echo("📦 Génération du DwC-A...")
    path = generate_dwca(df_mapped, output_dir)
    typer.echo(f"🎉 Archive générée : {path}")


if __name__ == "__main__":
    app()
