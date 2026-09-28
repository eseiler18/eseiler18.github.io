---
pub: stiff-transfer-learning-for-physics-informed
tldr: "Vanilla PINNs fail on stiff differential equations. STL-PINNs train a multi-head PINN in a mildly stiff regime, then transfer to highly stiff regimes in one shot, without retraining."
teaser:
  src: /projects/stiff-transfer-pinns/teaser.jpg
  caption: "STL-PINN pipeline: a multi-head PINN is trained in the low-stiff regime (α < α₀); its latent space H is then reused to compute one-shot solutions in the high-stiff regime (α > α₀)."
figures:
  - src: /projects/stiff-transfer-pinns/results.jpg
    wide: true
    caption: "Results on stiff ODEs (OHO, NCFF, Duffing) and on the AR PDE: solutions learned in the training regime (top) and transferred to much stiffer regimes (bottom) match the Radau reference solver."
---

This work comes from my Master's thesis at Harvard University with Prof. Pavlos Protopapas.
