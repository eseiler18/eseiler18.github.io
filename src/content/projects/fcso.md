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
    - { name: "Car · drag", left: /projects/fcso/car_vecset_gd_v2.gif, right: /projects/fcso/car_vecset_fcso_v2.gif }
    - { name: "Bike · stiffness", left: /projects/fcso/velo_hunyuan_gd.gif, right: /projects/fcso/velo_hunyuan_fcso.gif }
---

## Why it matters

Modern 3D generative models such as VecSet or Hunyuan3D are extremely expressive, but valid shapes only occupy a thin manifold of their high-dimensional latent space.
When we optimize a shape for an engineering objective, plain gradient descent quickly leaves this manifold and the shape stops being valid: we call this **manifold drift**.
Existing fixes either rely on a delicate guidance trade-off or are too costly for large models.

## How FCSO works

**Optimize freely, correct strictly.** FCSO alternates two phases: a few free gradient steps on the objective,
then a correction where the latent is partially re-noised and a pre-trained flow-matching model carries it back onto the manifold of valid shapes.
Repeating this cycle keeps improving the objective without accumulating geometric errors, and works with pre-trained models, without any retraining.

<figure>
  <img src="/projects/fcso/method.jpg" alt="FCSO method diagram" loading="lazy" />
  <figcaption>FCSO alternates gradient-based optimization (Phase 1) and a guided flow-matching correction (Phase 2), repeated K times.</figcaption>
</figure>

## Results

We evaluate FCSO on three tasks of increasing complexity: reducing the volume of chairs, reducing the aerodynamic drag of cars (confirmed with CFD simulations),
and maximizing the stiffness of objects under load with the Hunyuan3D foundation model.
At the same objective value, FCSO produces the most realistic shapes compared to state-of-the-art baselines, and the gap grows with the size of the model.

<div class="table-wrap">

| Task (shape prior) | GD | FMG | D-Flow | ICTM | SGO | **FCSO** |
|---|---:|---:|---:|---:|---:|---:|
| Chair volume −70% (3DShape2VecSet) | 88.1 | 43.1 | 56.9 | 91.7 | 32.7 | **31.8** |
| Car drag −30% (3DShape2VecSet) | 132.8 | 100.2 | 108.8 | 101.7 | 107.7 | **89.1** |
| Bicycle compliance −80% (Hunyuan3D) | 43.1 | 28.8 | OOM | 26.8 | 28.8 | **21.3** |
| Chair compliance −65% (Hunyuan3D) | 68.2 | 55.7 | OOM | 55.9 | 55.1 | **41.3** |

</div>
<p class="table-caption">Shape realism (FID on Inception features, lower is better), measured once every method has reached the same objective reduction. OOM: out of memory.</p>

See the [paper](https://arxiv.org/abs/2608.07199) for the full benchmark and ablations.
