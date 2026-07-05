"""CLI entry point: python main.py --invoice_path=... or python main.py --setup"""
import argparse
import json

from setup_db import setup_db
from src.invoice_agents.graph import build_graph


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--invoice_path")
    parser.add_argument("--setup", action="store_true")
    args = parser.parse_args()

    if args.setup:
        setup_db()
        print("Inventory database ready at data/inventory.db")
        return

    if not args.invoice_path:
        parser.error("--invoice_path is required unless --setup is passed")

    graph = build_graph()
    state = graph.invoke(
        {
            "invoice_path": args.invoice_path,
            "validation_flags": [],
            "reflection_count": 0,
            "steps_taken": [],
        }
    )

    result = {
        "invoice_path": args.invoice_path,
        "status": "PAID" if state.get("approval_decision") == "APPROVE" else "REJECTED",
        "extracted_invoice": state.get("extracted_invoice"),
        "validation_flags": state.get("validation_flags"),
        "approval_decision": state.get("approval_decision"),
        "approval_reasoning": state.get("approval_reasoning"),
        "reflection_count": state.get("reflection_count"),
        "payment_result": state.get("payment_result"),
        "rejection_log": state.get("rejection_log"),
        "steps_taken": state.get("steps_taken"),
    }
    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
