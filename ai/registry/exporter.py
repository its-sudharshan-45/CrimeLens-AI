"""
ai/registry/exporter.py
========================
Model Compression & Multi-Format Export Pipeline:
  1. TorchScript (.ts) — C++ / LibTorch production deployment
  2. ONNX (.onnx) — Cross-platform inference engine export
  3. Dynamic Quantization (.pt) — INT8 weight quantization for CPU acceleration
"""

import os
import torch
import torch.nn as nn
import logging
from typing import Dict, Any, Optional, cast

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Check ONNX availability
try:
    import onnx
    ONNX_AVAILABLE = True
except ImportError:
    ONNX_AVAILABLE = False


class ModelExporter:
    """
    Exports trained PyTorch models to TorchScript, ONNX, and Quantized formats.
    """

    def __init__(self, models_dir: str = "ai/models") -> None:
        self.models_dir = models_dir
        os.makedirs(self.models_dir, exist_ok=True)

    def export_torchscript(self, model: nn.Module, sample_input: torch.Tensor, filename: str = "crime_classifier.ts") -> str:
        """Export model to TorchScript bytecode format."""
        model.eval()
        filepath = os.path.join(self.models_dir, filename)

        try:
            scripted_model = torch.jit.trace(model, sample_input)
            cast(Any, scripted_model).save(filepath)
            logger.info(f"Exported TorchScript model to {filepath}")
            return filepath
        except Exception as e:
            logger.warning(f"TorchScript tracing fallback: {e}")
            try:
                scripted_model = torch.jit.script(model)
                cast(Any, scripted_model).save(filepath)
                logger.info(f"Exported TorchScript model (script mode) to {filepath}")
                return filepath
            except Exception as e2:
                logger.error(f"Failed to export TorchScript model: {e2}")
                return ""

    def export_onnx(
        self,
        model: nn.Module,
        sample_input: torch.Tensor,
        filename: str = "crime_classifier.onnx",
        input_names: Optional[list] = None,
        output_names: Optional[list] = None,
    ) -> str:
        """Export model to Open Neural Network Exchange (ONNX) format."""
        model.eval()
        filepath = os.path.join(self.models_dir, filename)

        if input_names is None:
            input_names = ["input_features"]
        if output_names is None:
            output_names = ["output_logits"]

        try:
            torch.onnx.export(
                model,
                (sample_input,),
                filepath,
                export_params=True,
                opset_version=14,
                do_constant_folding=True,
                input_names=input_names,
                output_names=output_names,
                dynamic_axes={input_names[0]: {0: "batch_size"}, output_names[0]: {0: "batch_size"}},
            )
            logger.info(f"Exported ONNX model to {filepath}")
            return filepath
        except Exception as e:
            logger.error(f"Failed to export ONNX model: {e}")
            return ""

    def export_quantized(self, model: nn.Module, filename: str = "crime_classifier_quantized.pt") -> str:
        """Export dynamically quantized (INT8 linear weights) PyTorch model for CPU acceleration."""
        model.eval()
        filepath = os.path.join(self.models_dir, filename)

        try:
            quantized_model = torch.quantization.quantize_dynamic(
                model, {nn.Linear}, dtype=torch.qint8
            )
            torch.save(quantized_model.state_dict(), filepath)
            logger.info(f"Exported Dynamic Quantized INT8 model to {filepath}")
            return filepath
        except Exception as e:
            logger.error(f"Failed to quantize model: {e}")
            return ""

    def export_all(
        self,
        model: nn.Module,
        sample_input: torch.Tensor,
        base_name: str = "crime_classifier",
    ) -> Dict[str, str]:
        """Export model to all three formats: TorchScript, ONNX, and Quantized."""
        ts_path = self.export_torchscript(model, sample_input, f"{base_name}.ts")
        onnx_path = self.export_onnx(model, sample_input, f"{base_name}.onnx")
        quant_path = self.export_quantized(model, f"{base_name}_quantized.pt")

        return {
            "torchscript": ts_path,
            "onnx": onnx_path,
            "quantized": quant_path,
        }
