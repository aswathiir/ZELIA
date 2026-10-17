import json
from pathlib import Path
from typing import Optional, Dict, Any

GRAPH_DIR = Path("question_graphs")

class QuestionGraph:
    def __init__(self, graph_dict: Dict[str, Any]):
        self.graph_id = graph_dict["graph_id"]
        self.version = graph_dict["version"]
        self.first_question_id = graph_dict["first_question_id"]
        # map id -> question dict
        self.questions_by_id = {q["id"]: q for q in graph_dict["questions"]}

    def get_first_question(self) -> Dict[str, Any]:
        return self.questions_by_id[self.first_question_id]

    def get_question(self, qid: str) -> Optional[Dict[str, Any]]:
        return self.questions_by_id.get(qid)

    def get_next_question(self, current_question: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        next_id = current_question.get("next")
        if not next_id:
            return None
        return self.get_question(next_id)

def load_graph(graph_name: str = "tamil_nadu_v1") -> QuestionGraph:
    path = GRAPH_DIR / f"{graph_name}.json"
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    return QuestionGraph(data)

if __name__ == "__main__":
    graph = load_graph()
    q = graph.get_first_question()
    while q is not None:
        print("Q:", q["id"], "-", q["text"])
        q = graph.get_next_question(q)
