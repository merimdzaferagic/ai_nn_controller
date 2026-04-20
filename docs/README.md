# Building Documentation Locally

```shell
cd docs
pip install -r requirements.txt
make html
```

The built documentation will be in `docs/_build/html/`. Open `index.html` to view.

For live preview during editing:

```shell
make livehtml
```

---
# GitHub Pages Deployment

The GitHub Actions workflow runs **manually**:

1. Trigger the workflow from the Actions tab
2. It builds the docs and deploys to GitHub Pages

## Setup (one-time)

1. Push changes to your repository
2. Enable GitHub Pages in repository settings:
   - Go to Settings → Pages
   - Under "Build and deployment", select GitHub Actions as the source
3. Go to Actions and run the "Deploy Documentation" workflow

## Documentation URL

Once deployed, documentation will be available at:

```
https://<your-username>.github.io/<repository-name>/
```

---
# Key Features

- Sphinx with Read the Docs theme
- Markdown support via MyST parser
- Code blocks with syntax highlighting
- Built-in search
- Mobile responsive
