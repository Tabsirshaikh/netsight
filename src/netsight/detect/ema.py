"""Exponential moving average of model weights (as in the official D-FINE / RT-DETR recipes).

The averaged weights change slowly, so the model evaluated and saved is less sensitive to which
epoch happens to look best on small, noisy validation sets.
"""

from __future__ import annotations

import copy
import math

import torch


class ModelEMA:
    def __init__(self, model: torch.nn.Module, decay: float = 0.9998, warmup: int = 1000) -> None:
        if not 0.0 < decay < 1.0:
            raise ValueError("decay must be in (0, 1)")
        self.module = copy.deepcopy(model).eval()
        for p in self.module.parameters():
            p.requires_grad_(False)
        self.decay, self.warmup, self.updates = decay, warmup, 0

    def current_decay(self) -> float:
        """Ramp from 0 so early, random weights are forgotten quickly."""
        return self.decay * (1.0 - math.exp(-self.updates / self.warmup))

    @torch.no_grad()
    def update(self, model: torch.nn.Module) -> None:
        self.updates += 1
        d = self.current_decay()
        live = model.state_dict()
        for name, value in self.module.state_dict().items():
            if value.dtype.is_floating_point:
                value.mul_(d).add_(live[name].detach(), alpha=1.0 - d)
            else:
                value.copy_(live[name])
