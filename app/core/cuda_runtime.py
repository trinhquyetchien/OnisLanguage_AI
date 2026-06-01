from __future__ import annotations

import ctypes
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

CUDA_LIBRARY_DIRS = [
    Path("/usr/local/lib/ollama/cuda_v12"),
    Path("/usr/local/lib/ollama/cuda_v13"),
]

_CUDA_PRELOADED = False


def bootstrap_cuda_library_path() -> None:
    existing = os.environ.get("LD_LIBRARY_PATH", "")
    paths = [str(path) for path in CUDA_LIBRARY_DIRS if path.exists()]
    if existing:
        paths.append(existing)
    if paths:
        os.environ["LD_LIBRARY_PATH"] = ":".join(paths)


def preload_ctranslate2_cuda_libraries() -> None:
    global _CUDA_PRELOADED
    if _CUDA_PRELOADED:
        return

    candidate_libs = [
        Path("/usr/local/lib/ollama/cuda_v12/libcudart.so.12"),
        Path("/usr/local/lib/ollama/cuda_v12/libcublas.so.12"),
        Path("/usr/local/lib/ollama/cuda_v12/libcublasLt.so.12"),
        Path("/usr/local/lib/ollama/mlx_cuda_v13/libcudnn.so.9"),
        Path("/usr/local/lib/ollama/mlx_cuda_v13/libcudnn_ops.so.9"),
        Path("/usr/local/lib/ollama/mlx_cuda_v13/libcudnn_cnn.so.9"),
        Path("/usr/local/lib/ollama/mlx_cuda_v13/libcudnn_adv.so.9"),
        Path("/usr/local/lib/ollama/mlx_cuda_v13/libcudnn_graph.so.9"),
        Path("/usr/local/lib/ollama/mlx_cuda_v13/libcudnn_heuristic.so.9"),
        Path("/usr/local/lib/ollama/mlx_cuda_v13/libcudnn_engines_runtime_compiled.so.9"),
        Path("/usr/local/lib/ollama/mlx_cuda_v13/libcudnn_engines_precompiled.so.9"),
    ]

    loaded_any = False
    for library_path in candidate_libs:
        if not library_path.exists():
            continue
        try:
            ctypes.CDLL(str(library_path), mode=ctypes.RTLD_GLOBAL)
            loaded_any = True
        except OSError as exc:
            logger.warning("Failed to preload CUDA library %s: %s", library_path, exc)

    if loaded_any:
        _CUDA_PRELOADED = True

