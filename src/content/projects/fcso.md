---
pub: flow-corrected-shape-optimization-taming-manifold
tldr: "Gradient-based optimization in the latent space of large 3D generative models drifts off the manifold of valid shapes. FCSO alternates free gradient steps on the objective with a flow-matching correction that brings the latent back onto the manifold: optimize freely, correct strictly."
teaser:
  src: /projects/fcso/figure1.jpg
  caption: "(a) Manifold drift: gradient descent reduces bike compliance and car drag, but the shapes stop being valid. (b) FCSO reaches the same objective values while the shapes stay valid. (c) FCSO alternates gradient descent (GD) steps and flow-matching (FM) corrections, shown here for volume reduction."
video:
  src: /projects/fcso/fcso_explainer_v2.mp4
  poster: /projects/fcso/poster_v2.jpg
  caption: "A 2.5-minute explainer of manifold drift and FCSO (with voice-over and captions)."
comparisons:
  title: Gradient descent vs. FCSO
  caption: "Same starting shapes and same objective value reached: plain gradient descent breaks the shapes, FCSO keeps them valid."
  labels: [Gradient descent, FCSO (ours)]
  rows:
    - { name: "Chair · volume", left: /projects/fcso/chair_vecset_gd.gif, right: /projects/fcso/chair_vecset_fcso.gif }
    - { name: "Car · drag", left: /projects/fcso/car_vecset_gd.gif, right: /projects/fcso/car_vecset_fcso.gif }
    - { name: "Bike · stiffness", left: /projects/fcso/velo_hunyuan_gd.gif, right: /projects/fcso/velo_hunyuan_fcso.gif }
---

## Method

Modern 3D generative models decode a latent code into a shape. Valid shapes lie on a thin manifold
of that latent space, and the manifold takes up a smaller and smaller share of the space as models get bigger.
Plain gradient descent on an engineering objective ignores the manifold and drifts away from it.
We call this **manifold drift**.

Existing fixes built on flow matching either do objective guidance and generation in a single pass,
which forces a trade-off, or backpropagate through the whole flow, which does not scale to large models.
**FCSO gives each job its own step** and repeats the following cycle:

1. **Optimize:** take a few plain gradient steps on the objective.
2. **Correct:** partially re-noise the latent, then let a pre-trained flow model carry it back onto the
   manifold, guided by the objective value reached in step 1.

Each cycle makes progress on the objective, then returns the latent to the manifold. FCSO works with generative priors ranging from
simple vector latent spaces to large-scale models such as Hunyuan3D, on tasks such as aerodynamic
drag reduction, volume reduction and compliance optimization.
