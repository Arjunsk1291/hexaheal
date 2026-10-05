#!/usr/bin/env bash
# Run on YOUR machine after `gh auth login`.
# Usage: ./push.sh [public|private]   (default: private until you choose)
# Pages needs a public repo on the free tier; private skips Pages.
set -euo pipefail
VIS=${1:-private}
case "$VIS" in public|private) ;; *) echo 'usage: ./push.sh [public|private]'; exit 1;; esac
gh auth status
gh repo create neurowalker --$VIS --source=. --remote=origin --push \
  --description "Simulated 18-DOF hexapod with a connectome-inspired spiking controller, benchmarked against PPO and a tripod CPG. Simulation only."
gh repo edit --add-topic robotics --add-topic mujoco --add-topic ros2 --add-topic connectome --add-topic drosophila --add-topic reinforcement-learning --add-topic hexapod --add-topic simulation
git tag -a v0.1.0 -m "NeuroWalker v0.1.0"
git push origin v0.1.0
[ -f release_artifacts/ppo_residual.zip ] && gh release create v0.1.0 release_artifacts/* --title "NeuroWalker v0.1.0" --notes "Checkpoints and result files. Simulation only." || gh release create v0.1.0 --title "NeuroWalker v0.1.0" --notes "Simulation only."
OWNER=$(gh api user -q .login)
if [ "$VIS" = public ]; then
gh api -X POST "repos/$OWNER/neurowalker/pages" -f build_type=workflow || gh api -X PUT "repos/$OWNER/neurowalker/pages" -f build_type=workflow
fi
echo "Repo: https://github.com/$OWNER/neurowalker"
[ "$VIS" = public ] && echo "Pages (after the Pages workflow finishes): https://$OWNER.github.io/neurowalker/"
true
