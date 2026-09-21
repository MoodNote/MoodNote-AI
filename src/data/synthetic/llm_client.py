"""
Batched chat generation with a Hugging Face causal LM (Colab T4, 4-bit).

torch/transformers are imported lazily so modules that only read generated JSONL do not pay
the import cost.
"""


class HFClient:
    """Chat-model wrapper used for both generation and cross-LLM auditing."""

    def __init__(self, model_id: str, load_in_4bit: bool = True) -> None:
        """
        Load tokenizer and model.

        Args:
            model_id: Hugging Face model id (e.g. "Qwen/Qwen3-8B")
            load_in_4bit: Quantize to 4-bit NF4 with bitsandbytes (needed for 8B on a T4)
        """
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

        self.model_id = model_id
        # Left padding: batched generation appends new tokens on the right.
        self.tokenizer = AutoTokenizer.from_pretrained(model_id, padding_side="left")
        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token

        quantization = (
            BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_quant_type="nf4",
                bnb_4bit_compute_dtype=torch.float16,  # T4 has no bf16
            )
            if load_in_4bit
            else None
        )
        self.model = AutoModelForCausalLM.from_pretrained(
            model_id, device_map="auto", dtype=torch.float16, quantization_config=quantization
        )

        eos = self.model.generation_config.eos_token_id
        self.eos_ids = set(eos if isinstance(eos, list) else [eos])

    def generate(
        self,
        batch_messages: list[list[dict[str, str]]],
        *,
        max_new_tokens: int,
        temperature: float = 0.0,
        top_p: float = 1.0,
        repetition_penalty: float = 1.0,
        seed: int = 0,
    ) -> list[tuple[str, bool]]:
        """
        Generate one reply per conversation.

        Args:
            batch_messages: One chat (list of role/content messages) per output
            max_new_tokens: Generation length cap
            temperature: Sampling temperature; 0 means greedy decoding
            top_p: Nucleus sampling threshold (ignored when greedy)
            repetition_penalty: Repetition penalty (1.0 = off)
            seed: Seed set right before generating, so a resumed run repeats the same batch

        Returns:
            list of (reply text, truncated) — truncated means max_new_tokens was hit before EOS
        """
        import torch
        from transformers import set_seed

        set_seed(seed)
        prompts = [
            # enable_thinking=False turns off Qwen3's <think> block; Llama's template ignores it.
            self.tokenizer.apply_chat_template(
                messages, tokenize=False, add_generation_prompt=True, enable_thinking=False
            )
            for messages in batch_messages
        ]
        # The chat template already contains the BOS token.
        inputs = self.tokenizer(
            prompts, return_tensors="pt", padding=True, add_special_tokens=False
        ).to(self.model.device)

        do_sample = temperature > 0
        with torch.inference_mode():
            output = self.model.generate(
                **inputs,
                max_new_tokens=max_new_tokens,
                do_sample=do_sample,
                # Greedy: None also clears the model's default sampling knobs.
                temperature=temperature if do_sample else None,
                top_p=top_p if do_sample else None,
                repetition_penalty=repetition_penalty,
                pad_token_id=self.tokenizer.pad_token_id,
            )

        new_tokens = output[:, inputs["input_ids"].shape[1] :]
        texts = self.tokenizer.batch_decode(new_tokens, skip_special_tokens=True)
        truncated = [not self.eos_ids.intersection(row.tolist()) for row in new_tokens]
        return list(zip(texts, truncated, strict=True))
