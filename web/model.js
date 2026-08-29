// The whole classifier. Three fully-connected layers with batch-norm already
// folded into them at export time (ml/export_web_model.py), so there is nothing
// to run but two matrix multiplies and an argmax.
// ml/tests/test_model_parity.py runs this file against PyTorch and fails if the
// two ever disagree by more than float noise.

export class Classifier {
  constructor(weights) {
    this.labels = weights.labels;
    this.layers = weights.layers.map((l) => ({
      in: l.in,
      out: l.out,
      w: Float32Array.from(l.w),
      b: Float32Array.from(l.b),
      relu: l.relu,
    }));
    this.prototypes = weights.prototypes || {};
  }

  static async load(url) {
    const res = await fetch(url);
    if (!res.ok) throw new Error(`could not load the model from ${url}: ${res.status}`);
    return new Classifier(await res.json());
  }

  forward(features) {
    let x = features;
    for (const layer of this.layers) {
      const out = new Float32Array(layer.out);
      for (let o = 0; o < layer.out; o++) {
        let sum = layer.b[o];
        const base = o * layer.in;
        for (let i = 0; i < layer.in; i++) sum += layer.w[base + i] * x[i];
        out[o] = layer.relu && sum < 0 ? 0 : sum;
      }
      x = out;
    }
    return x;
  }

  // Softmax over the logits, returned sorted. Confidence here is the model's
  // own probability, which is not the same thing as being right -- the page
  // says so where it displays it.
  predict(features) {
    const logits = this.forward(features);
    let max = -Infinity;
    for (const v of logits) if (v > max) max = v;
    let total = 0;
    const probs = new Float32Array(logits.length);
    for (let i = 0; i < logits.length; i++) {
      probs[i] = Math.exp(logits[i] - max);
      total += probs[i];
    }
    const ranked = [];
    for (let i = 0; i < probs.length; i++) {
      ranked.push({ label: this.labels[i], confidence: probs[i] / total });
    }
    ranked.sort((a, b) => b.confidence - a.confidence);
    return ranked;
  }
}
