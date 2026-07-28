# backend/core/hierarchy.py
ORG_CHART = {
    "CEO": {"title": "Chief Executive Officer", "role": "Strategic decision engine. Analyzes tasks, selects departments, sets company direction.", "reports_to": None, "manages": ["backend","security","devops","ai_research","architecture"]},
    "backend":      {"title": "Backend Engineering Department",    "role": "APIs, databases, services, backend architecture.", "reports_to": "CEO", "manages": []},
    "security":     {"title": "Security Department",               "role": "Threat modeling, auth, encryption, compliance.",   "reports_to": "CEO", "manages": []},
    "devops":       {"title": "DevOps & Infrastructure Department", "role": "Infrastructure, CI/CD, scaling, monitoring.",      "reports_to": "CEO", "manages": []},
    "ai_research":  {"title": "AI Research Department",            "role": "LLM strategy, model optimization, AI roadmap.",   "reports_to": "CEO", "manages": []},
    "architecture": {"title": "System Architecture Department",    "role": "System design, data flow, resilience strategy.",   "reports_to": "CEO", "manages": []}
}

def get_active_structure(selected):
    return {
        "CEO": {"title": ORG_CHART["CEO"]["title"], "role": ORG_CHART["CEO"]["role"], "active_departments": selected},
        "departments": {d: {"title": ORG_CHART[d]["title"], "role": ORG_CHART[d]["role"], "reports_to": "CEO"} for d in selected if d in ORG_CHART}
    }

def get_full_chart(): return ORG_CHART
