# Publishing this repo (needs your GitHub login)

The build environment had no GitHub login and no credentials were requested or stored. Everything is committed locally.

```bash
gh auth login            # once, on your machine
cd neurowalker           # or unzip neurowalker-v0.1.0.zip first, then: git status
./push.sh public         # or: ./push.sh private (Pages is skipped on private repos, free tier). Creates the repo, pushes, tags v0.1.0, release, enables Pages
```

Manual equivalent: `gh repo create neurowalker --public (or --private) --source=. --push`, then in the repo settings choose Pages -> Source: GitHub Actions.
The Pages workflow (`.github/workflows/pages.yml`) builds `dashboard/` from the precomputed files in `dashboard/public/data`.
