# backend/agents/devops_agent.py — Phase 2+3: reads backend + architecture context
import json, re
from backend.core.llm_provider import llm
from backend.core.logger import logger


def _extract(text):
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if m:
        try: return json.loads(m.group())
        except: pass
    return None


async def devops_agent(task: str, ceo_strategy: str = "", project_brief: dict = None, inter_context: str = "") -> dict:
    context_block = f"\nContext from other departments:\n{inter_context}\n" if inter_context else ""
    prompt = (
        "You are a Principal DevOps Architect at an MNC-level tech company.\n\n"
        "CEO Strategic Direction: " + ceo_strategy + "\n"
        + context_block +
        "Analyze the business idea and return ONLY valid JSON:\n"
        '{"department":"DevOps & Infrastructure","infrastructure":{"cloud_provider":"...","architecture":"...","containerization":"..."},'
        '"ci_cd":{"pipeline_tool":"...","stages":["..."],"deployment_strategy":"..."},'
        '"scaling":{"strategy":"...","auto_scaling":"...","load_balancing":"..."},'
        '"monitoring":{"tools":["..."],"alerting":"...","logging":"..."}}\n\n'
        "Business idea: " + task + "\n"
    )
    logger.info("DevOps Agent | Generating plan...")
    raw = await llm.agenerate(prompt)
    parsed = _extract(raw)
    if parsed:
        parsed["department"] = "DevOps & Infrastructure"
        return parsed
    return {
        "department": "DevOps & Infrastructure",
        "infrastructure": {"cloud_provider": "AWS - enterprise grade.", "architecture": "Multi-AZ private subnets.", "containerization": "Docker + ECS/Kubernetes."},
        "ci_cd": {"pipeline_tool": "GitHub Actions.", "stages": ["Lint & Test", "Build Image", "Deploy Staging", "Deploy Production"], "deployment_strategy": "Blue-green zero downtime."},
        "scaling": {"strategy": "Horizontal stateless scaling.", "auto_scaling": "Scale at 70% CPU.", "load_balancing": "AWS ALB health checks."},
        "monitoring": {"tools": ["Prometheus + Grafana", "CloudWatch"], "alerting": "PagerDuty on error rate >1%.", "logging": "ELK Stack 30-day retention."}
    }