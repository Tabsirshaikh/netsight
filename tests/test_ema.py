import torch

from netsight.detect.ema import ModelEMA


def test_ema_tracks_a_moving_weight_and_lags_it():
    model = torch.nn.Linear(1, 1, bias=False)
    with torch.no_grad():
        model.weight.fill_(0.0)
    ema = ModelEMA(model, decay=0.9, warmup=1)
    for _ in range(200):
        with torch.no_grad():
            model.weight.fill_(1.0)
        ema.update(model)
    assert abs(float(ema.module.weight) - 1.0) < 1e-3
    with torch.no_grad():
        model.weight.fill_(2.0)
    ema.update(model)
    assert 1.0 < float(ema.module.weight) < 1.2  # moves only a little per step


def test_ema_copy_is_independent_and_frozen():
    model = torch.nn.Linear(2, 1)
    ema = ModelEMA(model)
    assert all(not p.requires_grad for p in ema.module.parameters())
    with torch.no_grad():
        model.weight.add_(5.0)
    assert not torch.allclose(model.weight, ema.module.weight)


def test_first_update_copies_live_weights_during_warmup():
    model = torch.nn.Linear(1, 1, bias=False)
    ema = ModelEMA(model, decay=0.9999, warmup=1000)
    with torch.no_grad():
        model.weight.fill_(3.0)
    ema.update(model)  # decay ~0.001: almost a copy
    assert abs(float(ema.module.weight) - 3.0) < 0.01
