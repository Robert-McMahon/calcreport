"""Scaffold a new calcreport calculation project.

Usage (no existing environment needed):

    uvx --from "git+https://github.com/Robert-McMahon/calcreport" \\
        calcreport-init ~/projects/30040-CLIENT-PROJECT

Creates the project directory with a pyproject (calcreport[marimo] from
git), a starter marimo report notebook, images/, README, .gitignore, a
local git repository, and a synced .venv ready for `marimo edit`.
"""

import argparse
import datetime
import re
import shutil
import subprocess
import sys
from importlib import resources
from pathlib import Path


def parse_project_name(folder_name):
    """Split '30040-CLIENT-PROJECT' into job number, client, project.

    Falls back gracefully when the folder name doesn't match the
    convention - the metadata lines in the notebook are easy to edit.
    """
    m = re.match(r'^(\d+)-([^-]+)-(.+)$', folder_name)
    if m:
        return m.group(1), m.group(2), m.group(3)
    m = re.match(r'^(\d+)[-_]?(.*)$', folder_name)
    if m and m.group(1):
        return m.group(1), m.group(2) or 'CLIENT', 'PROJECT'
    return '00000', 'CLIENT', folder_name or 'PROJECT'


def render_template(name, substitutions):
    text = resources.files('calcreport.project_template').joinpath(name) \
        .read_text(encoding='utf-8')
    for key, value in substitutions.items():
        text = text.replace('{{' + key + '}}', value)
    return text


def create_project(directory, client=None, project=None, title=None,
                   sync=True, git=True):
    """Create a calcreport project at `directory`. Returns the Path."""
    directory = Path(directory).expanduser().resolve()
    if directory.exists() and any(directory.iterdir()):
        raise SystemExit(f"Refusing to scaffold into non-empty directory: {directory}")

    jobnum, client_token, project_token = parse_project_name(directory.name)
    substitutions = {
        'jobnum': jobnum,
        'client': client or client_token,
        'project': project or project_token,
        'title': title or 'Engineering Calculation Report',
        'name': directory.name.lower(),
        'notebook': f'{jobnum}-001.py',
        'date': datetime.date.today().isoformat(),
    }

    directory.mkdir(parents=True, exist_ok=True)
    (directory / 'images').mkdir()
    (directory / 'pyproject.toml').write_text(
        render_template('pyproject.toml.tmpl', substitutions), encoding='utf-8')
    (directory / 'README.md').write_text(
        render_template('README.md.tmpl', substitutions), encoding='utf-8')
    (directory / '.gitignore').write_text(
        render_template('gitignore.tmpl', substitutions), encoding='utf-8')
    (directory / f'{jobnum}-001.py').write_text(
        render_template('notebook.py.tmpl', substitutions), encoding='utf-8')

    if git and shutil.which('git'):
        subprocess.run(['git', 'init', '-q'], cwd=directory, check=True)
        subprocess.run(['git', 'add', '-A'], cwd=directory, check=True)
        subprocess.run(['git', 'commit', '-q', '-m', 'Scaffold calcreport project'],
                       cwd=directory, check=False)

    if sync:
        if shutil.which('uv'):
            print('Running uv sync (first run downloads dependencies)...')
            subprocess.run(['uv', 'sync'], cwd=directory, check=True)
        else:
            print('uv not found - run `uv sync` in the project to create the venv.')

    return directory


def main():
    parser = argparse.ArgumentParser(
        description='Scaffold a new calcreport calculation project.')
    parser.add_argument('directory',
                        help='Project directory, e.g. ~/projects/30040-CLIENT-PROJECT. '
                             'The jobnum-CLIENT-PROJECT name prefills the cover metadata.')
    parser.add_argument('--client', help='Client name for the cover page '
                        '(default: parsed from the directory name).')
    parser.add_argument('--project', help='Project name for the cover page.')
    parser.add_argument('--title', help='Report title for the cover page.')
    parser.add_argument('--no-sync', action='store_true',
                        help='Skip creating the venv with uv sync.')
    parser.add_argument('--no-git', action='store_true',
                        help='Skip git init / initial commit.')
    args = parser.parse_args()

    directory = create_project(args.directory, client=args.client,
                               project=args.project, title=args.title,
                               sync=not args.no_sync, git=not args.no_git)

    jobnum = parse_project_name(directory.name)[0]
    print(f"""
Project created: {directory}

Next steps:
  cd {directory}
  # edit the cover metadata in {jobnum}-001.py, then author:
  uv run marimo edit {jobnum}-001.py

  # render the report:
  uv run marimo export ipynb --include-outputs {jobnum}-001.py -o {jobnum}-001.ipynb
  uv run notebooktohtml {jobnum}-001.ipynb {jobnum}-001.html --standalone --pdf

  # (--pdf needs a one-time: uv run playwright install chromium)
  # private remote when ready: gh repo create {directory.name} --private --source .
""")


if __name__ == '__main__':
    main()
