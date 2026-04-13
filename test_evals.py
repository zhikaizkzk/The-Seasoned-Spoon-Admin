import asyncio
import pytest
from dotenv import load_dotenv

from langsmith import testing as t
from openevals.llm import create_llm_as_judge
from openevals.prompts import HALLUCINATION_PROMPT

from evaluation.datasetadmin import EXAMPLES
from evaluation.fairness import FAIRNESS_PROMPT
from evaluation.prompt_injection import PROMPT_INJECTION_PROMPT
from evaluation.toxicity import TOXICITY_PROMPT
from services.chat_service import run_chat

load_dotenv()

try:
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
except AttributeError:
    pass


@pytest.fixture(params=EXAMPLES)
def example(request):
    return request.param


def hallucination_evaluator(inputs: dict, outputs: dict, context, reference_outputs: dict):
    evaluator = create_llm_as_judge(
        prompt=HALLUCINATION_PROMPT,
        model="openai:o3-mini",
        feedback_key="hallucination",
    )
    return evaluator(
        inputs=inputs,
        context=context,
        outputs=outputs,
        reference_outputs=reference_outputs,
    )


def toxicity_evaluator(inputs: dict, outputs: dict, reference_outputs: dict):
    evaluator = create_llm_as_judge(
        prompt=TOXICITY_PROMPT,
        model="openai:o3-mini",
        feedback_key="toxicity",
    )
    result = evaluator(
        inputs=inputs,
        outputs=outputs,
        reference_outputs=reference_outputs,
    )
    return {
        **result,
        "pass": bool(result.get("score")),
    }


def fairness_evaluator(inputs: dict, outputs: dict, reference_outputs: dict):
    evaluator = create_llm_as_judge(
        prompt=FAIRNESS_PROMPT,
        model="openai:o3-mini",
        feedback_key="fairness",
    )
    result = evaluator(
        inputs=inputs,
        outputs=outputs,
        reference_outputs=reference_outputs,
    )
    return {
        **result,
        "pass": bool(result.get("score")),
    }


def prompt_injection_evaluator(inputs: dict, outputs: dict, reference_outputs: dict):
    evaluator = create_llm_as_judge(
        prompt=PROMPT_INJECTION_PROMPT,
        model="openai:o3-mini",
        feedback_key="prompt_injection",
    )
    result = evaluator(
        inputs=inputs,
        outputs=outputs,
        reference_outputs=reference_outputs,
    )
    return {
        **result,
        "pass": bool(result.get("score")),
    }


@pytest.mark.langsmith
def test_model(example):
    t.log_inputs({
        "message": example["inputs"]["message"],
        "chat_history": example["inputs"]["chat_history"],
        "state": example["inputs"]["state"],
    })

    response = asyncio.run(
        run_chat(
            message=example["inputs"]["message"],
            history=example["inputs"]["chat_history"],
            state=example["inputs"]["state"],
        )
    )

    model_output = response["message"]["response"]

    t.log_outputs({
        "response": model_output,
        "candidateItem": response["message"].get("candidateItem"),
        "state_delta": response["message"].get("state_delta"),
    })

    tox_result = toxicity_evaluator(
        inputs={"message": example["inputs"]["message"]},
        outputs={"response": model_output},
        reference_outputs=example["outputs"],
    )
    assert tox_result["pass"], f"Expected non-toxic output, got {tox_result}"

    hall_result = hallucination_evaluator(
        inputs={"message": example["inputs"]["message"]},
        context=example.get("context", ""),
        outputs={"response": model_output},
        reference_outputs=example["outputs"],
    )
    assert bool(hall_result.get("score")), (
        f"Expected hallucination pass, got {hall_result}"
    )

    if not example.get("skip_fairness", False):
        fair_result = fairness_evaluator(
            inputs={"message": example["inputs"]["message"]},
            outputs={"response": model_output},
            reference_outputs=example["outputs"],
        )
        assert fair_result["pass"], f"Expected fairness pass, got {fair_result}"

    if not example.get("skip_prompt_injection", False):
        pi_result = prompt_injection_evaluator(
            inputs={"message": example["inputs"]["message"]},
            outputs={"response": model_output},
            reference_outputs=example["outputs"],
        )
        assert pi_result["pass"], f"Expected prompt injection pass, got {pi_result}"