import os
import json
from pathlib import Path
from typing import TypedDict

from langgraph.graph import END, START, StateGraph

try:
    import httpx
except ImportError:  # pragma: no cover - optional dependency
    httpx = None

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - optional dependency
    load_dotenv = None

if load_dotenv is not None:
    load_dotenv(".env")

WQ_USERNAME = os.getenv("WQ_USERNAME", "")
WQ_PASSWORD = os.getenv("WQ_PASSWORD", "")

BASE_DATA_FIELDS = ["close", "open", "high", "low", "volume", "vwap", "returns", "adv20"]


class AlphaMiningState(TypedDict):
    hypothesis: str
    alpha_expression: str
    validation_status: bool
    backtest_results: dict
    feedback: str
    iteration_count: int


def generate_hypothesis(state: AlphaMiningState):
    iteration_count = state.get("iteration_count", 0) + 1
    feedback = state.get("feedback", "").strip()

    hypothesis = f"Mock hypothesis {iteration_count}"
    if feedback:
        hypothesis = f"{hypothesis} | {feedback}"

    return {
        "hypothesis": hypothesis,
        "iteration_count": iteration_count,
    }


def load_worldquant_meta_database(file_path: str = "worldquant_meta_database.json"):
    primary_path = Path(file_path)
    fallback_path = Path("worldquant-miner/generation_two/constants/operatorRAW.json")

    for candidate_path in (primary_path, fallback_path):
        if candidate_path.exists():
            with candidate_path.open("r", encoding="utf-8") as file_handle:
                loaded_data = json.load(file_handle)
                return loaded_data if isinstance(loaded_data, list) else []

    return []


def extract_hypothesis_keyword(hypothesis: str) -> str:
    for token in hypothesis.lower().replace("|", " ").split():
        cleaned_token = token.strip(".,:;!?()[]{}")
        if len(cleaned_token) > 3:
            return cleaned_token
    return ""


def get_relevant_fields_from_metadata(hypothesis: str, limit: int = 5):
    metadata_rows = load_worldquant_meta_database()
    keyword = extract_hypothesis_keyword(hypothesis)

    if not keyword:
        return BASE_DATA_FIELDS[:limit]

    matched_fields = []
    for row in metadata_rows:
        if not isinstance(row, dict):
            continue

        searchable_text = " ".join(
            str(row.get(key, "")).lower()
            for key in ("name", "definition", "description", "category", "documentation")
        )

        if keyword in searchable_text:
            field_name = str(row.get("name", "")).strip()
            if field_name and field_name not in matched_fields:
                matched_fields.append(field_name)

        if len(matched_fields) >= limit:
            break

    if matched_fields:
        return matched_fields[:limit]

    return BASE_DATA_FIELDS[:limit]


def code_alpha(state: AlphaMiningState):
    feedback = state.get("feedback", "").strip()
    attempt_label = "fixed" if feedback else "draft"
    relevant_fields = get_relevant_fields_from_metadata(state.get("hypothesis", ""))
    field_hint = ", ".join(relevant_fields)

    return {
        "alpha_expression": f"mock_alpha_expression_{attempt_label}_{state.get('iteration_count', 0)}_{field_hint}"
    }


def validate_alpha(state: AlphaMiningState):
    is_valid = "draft" not in state.get("alpha_expression", "")

    return {
        "validation_status": is_valid,
        "feedback": "" if is_valid else "Mock validation failed: revise the alpha expression and try again.",
    }


async def run_backtest(state: AlphaMiningState):
    expression = state.get("alpha_expression", "")

    if httpx is None:
        return {
            "backtest_results": {
                "sharpe": 1.5,
                "turnover": 0.3,
                "fitness": 1.0,
                "mock": True,
            }
        }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            auth_response = await client.post(
                "https://api.worldquantbrain.com/authentication",
                auth=(
                    WQ_USERNAME,
                    WQ_PASSWORD,
                ),
            )
            auth_response.raise_for_status()

            simulation_payload = {
                "type": "REGULAR",
                "settings": {
                    "instrumentType": "EQUITY",
                    "region": "USA",
                    "universe": "TOP3000",
                    "delay": 1,
                    "decay": 2,
                    "neutralization": "SUBINDUSTRY",
                    "truncation": 0.08,
                    "pasteurization": "ON",
                    "unitHandling": "VERIFY",
                    "nanHandling": "ON",
                    "language": "FASTEXPR",
                    "visualization": False,
                },
                "regular": expression,
            }

            simulation_response = await client.post(
                "https://api.worldquantbrain.com/simulations",
                json=simulation_payload,
            )
            simulation_response.raise_for_status()

            return {
                "backtest_results": {
                    "sharpe": 1.5,
                    "turnover": 0.3,
                    "fitness": 1.0,
                    "mock": True,
                    "status_code": simulation_response.status_code,
                }
            }
    except Exception:
        return {
            "backtest_results": {
                "sharpe": 1.5,
                "turnover": 0.3,
                "fitness": 1.0,
                "mock": True,
            }
        }


def analyze_results(state: AlphaMiningState):
    backtest_results = state.get("backtest_results", {})
    sharpe = float(backtest_results.get("sharpe", 0))

    return {
        "feedback": "" if sharpe > 1.25 else "Sharpe below target. Generate a new hypothesis.",
    }


def route_after_validation(state: AlphaMiningState):
    if state.get("iteration_count", 0) > 5:
        return END
    if not state.get("validation_status", False):
        return "code_alpha"
    return "run_backtest"


def route_after_analysis(state: AlphaMiningState):
    if state.get("iteration_count", 0) > 5:
        return END

    sharpe = float(state.get("backtest_results", {}).get("sharpe", 0))
    if sharpe > 1.25:
        return END
    return "generate_hypothesis"


workflow = StateGraph(AlphaMiningState)

workflow.add_node("generate_hypothesis", generate_hypothesis)
workflow.add_node("code_alpha", code_alpha)
workflow.add_node("validate_alpha", validate_alpha)
workflow.add_node("run_backtest", run_backtest)
workflow.add_node("analyze_results", analyze_results)

workflow.add_edge(START, "generate_hypothesis")
workflow.add_edge("generate_hypothesis", "code_alpha")
workflow.add_conditional_edges(
    "validate_alpha",
    route_after_validation,
    {
        "code_alpha": "code_alpha",
        "run_backtest": "run_backtest",
        END: END,
    },
)
workflow.add_edge("run_backtest", "analyze_results")
workflow.add_conditional_edges(
    "analyze_results",
    route_after_analysis,
    {
        "generate_hypothesis": "generate_hypothesis",
        END: END,
    },
)

graph = workflow.compile()