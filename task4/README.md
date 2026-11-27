# Task 4 – Interactive Dashboard & Visualization

The dashboard imports Task 3's original `analysis.py` (branch `QJ8W7I-task-3`, commit `3fa27c6a3057010e0cf31361305f7e5263c3ffbb`) and calls `load_merged` and `run`. It embeds the resulting annual observations, country and regional summaries, regressions, and validation statistics in a static HTML page. The default source is the group's merged workbook, not the raw-source re-merge. Existing Task 3 files are not changed.

## Add to the repository (Windows PowerShell)

From the directory where you want the repository:

```powershell
git clone --branch QJ8W7I-task-3 https://github.com/alfiidan/sustainability-data-analytics.git
cd sustainability-data-analytics
git switch -c task-4
```

Extract the Netlify-ready ZIP into this repository root (the folder containing `analysis.py`). Then:

```powershell
git add task4 requirements.txt netlify.toml .gitignore
git commit -m "Add Task 4 interactive sustainability dashboard and Netlify build"
git push -u origin task-4
```

Requires write permission on the repository and an authenticated GitHub account. If the branch already exists, fetch and switch to it instead of creating it; inspect its contents before copying. Do not force-push.

## Build and preview locally

From the repository root:

```powershell
py -m pip install -r requirements.txt
py task4/build_dashboard.py --repo . --source merged --output dist/index.html --results dashboard_results
start dist/index.html
```

On Linux/macOS, substitute `python3` for `py` and open `dist/index.html` in a browser. Generated output directories are ignored by Git. The generated dashboard works without a backend.

## Netlify

Import the GitHub repository as a new project, select `task-4` as the production branch, leave the base directory at the root, and publish. `netlify.toml` sets the build command, publish directory `dist`, and Python 3.12. Netlify installs dependencies from root `requirements.txt` before invoking the build. No API keys or secrets are required. If the interface does not allow selecting the branch during import, set the production branch under Project configuration > Developer settings > Continuous deployment > Branches and deploy contexts, and trigger a deploy.

The site should publish `dist/index.html` at `/`. The intermediate statistical outputs in `dashboard_results/` remain outside the publish directory. For a manual deploy, build locally first and upload only `dist/` to https://app.netlify.com/drop. Manual deploys do not run the Python build.

## Notes

The dashboard provides country, region, time and indicator filters, Task 3's six decoupling categories, nine subregions, five comparison periods, regression metrics, charts and CSV export. Custom scopes use the same statistical definitions with the prepared annual observations. Results represent only the 43 matched countries, not worldwide coverage. Regression is descriptive, not causal.

The original Python pipeline against the actual workbook and the Netlify cloud build have not been executed in this environment. Verify the local build and Netlify deploy logs before submission.
