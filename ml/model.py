"""The classifier, and the one training loop shared by evaluation and shipping.

Evaluation and the shipped model must be trained by identical code, or the
number in the README describes a model nobody ever ran.
"""

import numpy as np
import torch
import torch.nn as nn

from features import FEATURE_DIM

HIDDEN = (256, 128)
EPOCHS = 60
BATCH_SIZE = 256
LR = 1e-3
WEIGHT_DECAY = 1e-4
NOISE_SIGMA = 0.015  # landmark jitter, in units of normalized hand size
SEED = 20260829


class LandmarkMLP(nn.Module):
    def __init__(self, n_classes, in_dim=FEATURE_DIM, hidden=HIDDEN):
        super().__init__()
        layers, prev = [], in_dim
        for h in hidden:
            layers += [nn.Linear(prev, h), nn.BatchNorm1d(h), nn.ReLU(), nn.Dropout(0.3)]
            prev = h
        layers.append(nn.Linear(prev, n_classes))
        self.net = nn.Sequential(*layers)

    def forward(self, x):
        return self.net(x)


def train(X, y, n_classes, epochs=EPOCHS, seed=SEED, verbose=False):
    """Fixed hyperparameters, fixed epoch count, no early stopping.

    Nothing here reads the test set -- not even to decide when to stop -- so the
    held-out numbers are not quietly tuned against the thing they measure.
    """
    torch.manual_seed(seed)
    np.random.seed(seed)

    device = "cpu"
    model = LandmarkMLP(n_classes).to(device)
    opt = torch.optim.AdamW(model.parameters(), lr=LR, weight_decay=WEIGHT_DECAY)
    sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=epochs)
    loss_fn = nn.CrossEntropyLoss(label_smoothing=0.05)

    Xt = torch.from_numpy(np.ascontiguousarray(X, dtype=np.float32))
    yt = torch.from_numpy(np.ascontiguousarray(y, dtype=np.int64))
    n = len(Xt)
    g = torch.Generator().manual_seed(seed)

    model.train()
    for epoch in range(epochs):
        perm = torch.randperm(n, generator=g)
        running = 0.0
        for i in range(0, n, BATCH_SIZE):
            idx = perm[i : i + BATCH_SIZE]
            if len(idx) < 2:  # BatchNorm needs more than one sample
                continue
            xb = Xt[idx]
            xb = xb + torch.randn(xb.shape, generator=g) * NOISE_SIGMA
            opt.zero_grad()
            loss = loss_fn(model(xb), yt[idx])
            loss.backward()
            opt.step()
            running += loss.item() * len(idx)
        sched.step()
        if verbose and (epoch + 1) % 20 == 0:
            print(f"  epoch {epoch + 1}/{epochs} loss {running / n:.4f}", flush=True)

    model.eval()
    return model


def predict(model, X, batch=4096):
    out = []
    with torch.no_grad():
        for i in range(0, len(X), batch):
            xb = torch.from_numpy(np.ascontiguousarray(X[i : i + batch], dtype=np.float32))
            out.append(model(xb).argmax(1).numpy())
    return np.concatenate(out) if out else np.array([], dtype=np.int64)
