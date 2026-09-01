"""Merge LoRA adapters, export ONNX, quantise to INT8.

    python -m prahari.ml.training.export_onnx

Produces exactly two files the runtime needs, both under ./models:

    prahari.onnx     INT8 token classifier, CPU execution provider
    tokenizer.json   the fast tokenizer, loaded locally by `tokenizers`

Nothing else is required at inference. The runtime never imports transformers,
never touches the HuggingFace hub, and never opens a socket.

Why INT8: a base-size encoder is ~110M params, ~440MB in fp32. Dynamic INT8
quantisation of the MatMul/Attention weights takes that to ~110MB and roughly
2-3x the CPU throughput, which is what brings a single report inside the 200ms
budget on a laptop with no GPU. Dynamic (not static) quantisation is used
because it needs no calibration set and the accuracy cost on token
classification is small — the export verifies that cost rather than assuming it.

Build-time only.
"""

from __future__ import annotations

import argparse
import json
import shutil
import time
from pathlib import Path

from prahari.data.annotation import BIO_LABELS, ID_TO_LABEL, LABEL_TO_ID
from prahari.ml.config import BASE_MODEL, MAX_LENGTH


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m prahari.ml.training.export_onnx")
    parser.add_argument("--adapters", type=Path, default=Path("models/lora-adapters"))
    parser.add_argument("--out-dir", type=Path, default=Path("models"))
    parser.add_argument("--model", default=BASE_MODEL)
    parser.add_argument("--opset", type=int, default=14)
    parser.add_argument("--no-quantise", action="store_true")
    args = parser.parse_args(argv)

    import numpy as np
    import torch
    from peft import PeftModel
    from transformers import AutoModelForTokenClassification, AutoTokenizer

    args.out_dir.mkdir(parents=True, exist_ok=True)
    fp32_path = args.out_dir / "prahari-fp32.onnx"
    int8_path = args.out_dir / "prahari.onnx"

    print("1/5  loading base model and merging adapters")
    base = AutoModelForTokenClassification.from_pretrained(
        args.model, num_labels=len(BIO_LABELS), id2label=ID_TO_LABEL, label2id=LABEL_TO_ID
    )
    model = PeftModel.from_pretrained(base, args.adapters)
    model = model.merge_and_unload()   # adapters folded into the base weights
    model.eval()

    print("2/5  saving tokenizer.json")
    tokenizer = AutoTokenizer.from_pretrained(args.adapters)
    tokenizer.save_pretrained(args.out_dir / "tokenizer-hf")
    src = args.out_dir / "tokenizer-hf" / "tokenizer.json"
    if not src.exists():
        raise SystemExit(
            "tokenizer.json missing — the fast tokenizer is required for offline "
            "inference (the runtime does not import transformers)."
        )
    shutil.copyfile(src, args.out_dir / "tokenizer.json")

    print("3/5  exporting ONNX (dynamic batch and sequence axes)")
    sample = tokenizer(
        "Sri B. Gogoi was working at monkey board at 8 mtr height. Safety belt nahi pehna tha.",
        return_tensors="pt", truncation=True, max_length=MAX_LENGTH,
    )
    input_names = [n for n in ("input_ids", "attention_mask", "token_type_ids") if n in sample]
    torch.onnx.export(
        model,
        tuple(sample[n] for n in input_names),
        str(fp32_path),
        input_names=input_names,
        output_names=["logits"],
        dynamic_axes={n: {0: "batch", 1: "sequence"} for n in [*input_names, "logits"]},
        opset_version=args.opset,
        do_constant_folding=True,
    )

    if args.no_quantise:
        shutil.copyfile(fp32_path, int8_path)
        print("4/5  quantisation skipped (--no-quantise)")
    else:
        print("4/5  quantising to INT8 (dynamic, weights only)")
        from onnxruntime.quantization import QuantType, quantize_dynamic

        quantize_dynamic(
            model_input=str(fp32_path),
            model_output=str(int8_path),
            weight_type=QuantType.QInt8,
            extra_options={"MatMulConstBOnly": True},
        )

    print("5/5  verifying the exported model on CPU")
    import onnxruntime as ort

    options = ort.SessionOptions()
    options.intra_op_num_threads = 1
    session = ort.InferenceSession(
        str(int8_path), sess_options=options, providers=["CPUExecutionProvider"]
    )
    feeds = {n: sample[n].numpy() for n in input_names if n in {i.name for i in session.get_inputs()}}

    onnx_logits = session.run(None, feeds)[0]
    with torch.no_grad():
        torch_logits = model(**{n: sample[n] for n in input_names}).logits.numpy()
    agreement = float(
        (onnx_logits.argmax(-1) == torch_logits.argmax(-1)).mean()
    )

    for _ in range(3):
        session.run(None, feeds)
    timings = []
    for _ in range(20):
        started = time.perf_counter()
        session.run(None, feeds)
        timings.append((time.perf_counter() - started) * 1000)
    timings.sort()

    report = {
        "onnx_int8": str(int8_path),
        "size_mb": round(int8_path.stat().st_size / 1e6, 1),
        "fp32_size_mb": round(fp32_path.stat().st_size / 1e6, 1),
        "argmax_agreement_with_torch": round(agreement, 4),
        "cpu_latency_p50_ms": round(timings[len(timings) // 2], 1),
        "cpu_latency_p95_ms": round(timings[int(len(timings) * 0.95)], 1),
        "opset": args.opset,
        "labels": len(BIO_LABELS),
    }
    (args.out_dir / "export_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")

    print("\n" + "=" * 62)
    for key, value in report.items():
        print(f"  {key:32s} {value}")
    print("=" * 62)
    if agreement < 0.98:
        print("  WARNING: INT8 disagrees with fp32 on >2% of tokens.")
        print("           Re-run with --no-quantise and compare before shipping.")
    if report["cpu_latency_p50_ms"] > 200:
        print("  WARNING: over the 200ms CPU budget. Reduce MAX_LENGTH or keep fp16 on GPU.")
    print("\n  The runtime picks this up automatically — no config change needed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
