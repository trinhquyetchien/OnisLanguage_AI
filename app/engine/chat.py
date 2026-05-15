from __future__ import annotations

import logging
import os
import json
from pathlib import Path
from typing import Any, Dict, List

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

from app.core.config import resolve_hf_local_snapshot, settings

logger = logging.getLogger(__name__)


class ChatEngine:
    def __init__(self) -> None:
        self.model = None
        self.tokenizer = None
        self.device = torch.device(self._resolve_device())
        # Redirect HuggingFace cache to project directory
        os.environ["HF_HOME"] = str(settings.CHAT_MODEL_DIR)

    @staticmethod
    def _resolve_device() -> str:
        requested = settings.CHAT_DEVICE
        if requested == "auto":
            return "cuda" if torch.cuda.is_available() else "cpu"
        if requested == "cuda" and torch.cuda.is_available():
            return "cuda"
        return "cpu"

    def load(self) -> None:
        self._load_resources()

    @staticmethod
    def _should_retry_on_cpu(exc: Exception) -> bool:
        message = str(exc).lower()
        return any(token in message for token in ("cuda", "cublas", "cudnn", "out of memory"))

    def _reset_to_cpu(self) -> None:
        logger.warning("Resetting chat runtime to CPU.")
        self.model = None
        self.tokenizer = None
        self.device = torch.device("cpu")

    def _load_resources(self) -> None:
        if self.model is None:
            model_name = settings.CHAT_MODEL
            model_path = resolve_hf_local_snapshot(settings.CHAT_MODEL_DIR, model_name)
            logger.info("Loading LLM model (%s) from local snapshot %s on %s...", model_name, model_path, self.device)
            
            self.tokenizer = AutoTokenizer.from_pretrained(
                str(model_path),
                local_files_only=True,
                trust_remote_code=True
            )
            try:
                self.model = AutoModelForCausalLM.from_pretrained(
                    str(model_path),
                    local_files_only=True,
                    device_map="auto" if self.device.type == "cuda" else "cpu",
                    torch_dtype=torch.float16 if self.device.type == "cuda" else torch.float32,
                    trust_remote_code=True
                )
            except RuntimeError as exc:
                if self.device.type == "cuda" and self._should_retry_on_cpu(exc):
                    logger.warning(
                        "Chat CUDA load failed (%s). Falling back to CPU for model %s.",
                        exc,
                        model_name,
                    )
                    self._reset_to_cpu()
                    self._load_resources()
                    return
                raise

    def _resolve_context_limit(self) -> int:
        model_max = getattr(self.tokenizer, "model_max_length", None)
        if isinstance(model_max, int) and 0 < model_max < 100000:
            return model_max

        cfg_max = getattr(getattr(self.model, "config", None), "max_position_embeddings", None)
        if isinstance(cfg_max, int) and cfg_max > 0:
            return cfg_max

        # Safe default for smaller chat models.
        return 512

    def generate_response(
        self,
        messages: List[Dict[str, str]],
        max_new_tokens: int = 256,
        *,
        do_sample: bool = True,
        temperature: float = 0.7,
        top_p: float = 0.9,
    ) -> str:
        self._load_resources()
        
        try:
            text = self.tokenizer.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=True
            )
            model_device = next(self.model.parameters()).device
            context_limit = self._resolve_context_limit()
            # Keep room for generated tokens to avoid context overflow during decode.
            max_input_tokens = max(32, context_limit - max_new_tokens)
            model_inputs = self.tokenizer(
                [text],
                return_tensors="pt",
                truncation=True,
                max_length=max_input_tokens,
            )
            model_inputs = {key: value.to(model_device) for key, value in model_inputs.items()}

            generation_kwargs = {
                **model_inputs,
                "max_new_tokens": max_new_tokens,
                "do_sample": do_sample,
            }
            if do_sample:
                generation_kwargs["temperature"] = temperature
                generation_kwargs["top_p"] = top_p

            generated_ids = self.model.generate(**generation_kwargs)
            
            generated_ids = [
                output_ids[len(input_ids):]
                for input_ids, output_ids in zip(model_inputs["input_ids"], generated_ids)
            ]

            response = self.tokenizer.batch_decode(generated_ids, skip_special_tokens=True)[0]
            return response
        except Exception as exc:
            logger.error("Error in ChatEngine: %s", exc)
            return f"Tôi xin lỗi, có lỗi xảy ra khi xử lý tin nhắn: {exc}"

    def explain_grammar(self, sentence: str) -> str:
        messages = [
            {"role": "system", "content": "Bạn là một giáo viên tiếng Nhật chuyên nghiệp. Hãy giải thích chi tiết cấu trúc ngữ pháp và từ vựng trong câu sau bằng tiếng Việt."},
            {"role": "user", "content": sentence}
        ]
        return self.generate_response(
            messages,
            max_new_tokens=192,
            do_sample=False,
            temperature=0.0,
            top_p=1.0,
        )

    def generate_exam(self, topic: str, count: int = 5) -> List[Dict[str, Any]]:
        prompt = f"""Hãy tạo một đề thi tiếng Nhật gồm {count} câu hỏi trắc nghiệm về chủ đề: {topic}.
Mỗi câu hỏi phải có chính xác 5 đáp án lựa chọn.
Trả về định dạng JSON là một danh sách các đối tượng câu hỏi với các trường:
- prompt: nội dung câu hỏi
- options: danh sách 5 đáp án
- correct_answer: đáp án đúng (phải nằm trong danh sách options)
- explanation: giải thích tại sao đáp án đó đúng (bằng tiếng Việt)
- kind: "multiple_choice"

Chỉ trả về JSON, không thêm văn bản khác."""

        messages = [
            {"role": "system", "content": "Bạn là một chuyên gia tạo đề thi tiếng Nhật. Bạn chỉ trả về dữ liệu định dạng JSON."},
            {"role": "user", "content": prompt}
        ]
        
        # Exam payload is verbose (prompt + 5 options + explanation per item),
        # so allocate a larger generation budget to avoid truncated outputs.
        max_new_tokens = max(320, min(1024, count * 220))
        response = self.generate_response(
            messages,
            max_new_tokens=max_new_tokens,
            do_sample=False,
            temperature=0.0,
            top_p=1.0,
        )

        parsed = self._parse_exam_questions(response)
        if parsed:
            return parsed

        logger.warning("Primary exam JSON parse failed, retrying with stricter prompt.")
        retry_messages = [
            {"role": "system", "content": "Bạn là một chuyên gia tạo đề thi tiếng Nhật. Trả về DUY NHẤT JSON array hợp lệ, không markdown, không giải thích."},
            {"role": "user", "content": (
                f"Tạo {count} câu hỏi trắc nghiệm tiếng Nhật chủ đề '{topic}'. "
                "Mỗi phần tử phải có đủ 5 khóa: prompt, options, correct_answer, explanation, kind. "
                "options phải có đúng 5 lựa chọn, kind luôn là 'multiple_choice'."
            )},
        ]
        retry_response = self.generate_response(
            retry_messages,
            max_new_tokens=max_new_tokens,
            do_sample=False,
            temperature=0.0,
            top_p=1.0,
        )
        parsed_retry = self._parse_exam_questions(retry_response)
        if parsed_retry:
            return parsed_retry

        logger.warning("Retry exam JSON parse failed, switching to marker-based fallback format.")
        fallback_messages = [
            {"role": "system", "content": "Bạn là chuyên gia tạo đề thi tiếng Nhật. Chỉ trả về theo đúng template marker."},
            {"role": "user", "content": (
                f"Tạo {count} câu hỏi trắc nghiệm tiếng Nhật chủ đề '{topic}'. "
                "Mỗi câu đúng format:\n"
                "###QUESTION###\n"
                "<nội dung>\n"
                "###OPTIONS###\n"
                "A) <đáp án 1>\nB) <đáp án 2>\nC) <đáp án 3>\nD) <đáp án 4>\nE) <đáp án 5>\n"
                "###ANSWER###\n"
                "<ghi nguyên văn 1 đáp án đúng trong 5 đáp án>\n"
                "###EXPLANATION###\n"
                "<giải thích ngắn>\n"
                "###END###\n"
                "Không thêm markdown và không thêm text khác."
            )},
        ]
        fallback_response = self.generate_response(
            fallback_messages,
            max_new_tokens=max_new_tokens,
            do_sample=False,
            temperature=0.0,
            top_p=1.0,
        )
        return self._parse_marker_exam_questions(fallback_response)

    @staticmethod
    def _clean_json_payload(raw: str) -> str:
        clean_json = (raw or "").strip()
        if clean_json.startswith("```json"):
            clean_json = clean_json[7:]
        if clean_json.startswith("```"):
            clean_json = clean_json[3:]
        if clean_json.endswith("```"):
            clean_json = clean_json[:-3]
        clean_json = clean_json.strip()

        start = clean_json.find("[")
        end = clean_json.rfind("]")
        if start != -1 and end != -1 and end > start:
            clean_json = clean_json[start:end + 1]
        return clean_json

    @staticmethod
    def _normalize_exam_item(item: Dict[str, Any]) -> Dict[str, Any] | None:
        prompt = str(item.get("prompt") or "").strip()
        options = item.get("options") or []
        if not isinstance(options, list):
            return None
        normalized_options = [str(opt).strip() for opt in options if str(opt).strip()]
        if len(normalized_options) != 5 or not prompt:
            return None

        correct = str(item.get("correct_answer") or "").strip()
        if correct and correct not in normalized_options:
            correct = normalized_options[0]

        return {
            "prompt": prompt,
            "options": normalized_options,
            "correct_answer": correct or normalized_options[0],
            "explanation": str(item.get("explanation") or "").strip(),
            "kind": "multiple_choice",
        }

    def _parse_exam_questions(self, raw: str) -> List[Dict[str, Any]]:
        clean_json = self._clean_json_payload(raw)
        try:
            payload = json.loads(clean_json)
        except Exception as exc:
            logger.error("Failed to parse AI exam response: %s", exc)
            return []

        if not isinstance(payload, list):
            return []

        results: List[Dict[str, Any]] = []
        for item in payload:
            if not isinstance(item, dict):
                continue
            normalized = self._normalize_exam_item(item)
            if normalized:
                results.append(normalized)
        return results

    def _parse_marker_exam_questions(self, raw: str) -> List[Dict[str, Any]]:
        text = (raw or "").strip()
        if not text:
            return []

        results: List[Dict[str, Any]] = []
        blocks = [block.strip() for block in text.split("###END###") if block.strip()]
        for block in blocks:
            if "###QUESTION###" not in block or "###OPTIONS###" not in block or "###ANSWER###" not in block:
                continue

            try:
                question_part = block.split("###QUESTION###", 1)[1].split("###OPTIONS###", 1)[0].strip()
                options_part = block.split("###OPTIONS###", 1)[1].split("###ANSWER###", 1)[0].strip()
                answer_part = block.split("###ANSWER###", 1)[1]
                if "###EXPLANATION###" in answer_part:
                    answer_text = answer_part.split("###EXPLANATION###", 1)[0].strip()
                    explanation_text = answer_part.split("###EXPLANATION###", 1)[1].strip()
                else:
                    answer_text = answer_part.strip()
                    explanation_text = ""
            except Exception:
                continue

            options: List[str] = []
            for line in options_part.splitlines():
                stripped = line.strip()
                if not stripped:
                    continue
                if len(stripped) > 2 and stripped[0] in "ABCDE" and stripped[1] == ")":
                    stripped = stripped[2:].strip()
                options.append(stripped)

            normalized = self._normalize_exam_item(
                {
                    "prompt": question_part,
                    "options": options[:5],
                    "correct_answer": answer_text,
                    "explanation": explanation_text,
                    "kind": "multiple_choice",
                }
            )
            if normalized:
                results.append(normalized)

        return results


chat_engine = ChatEngine()
