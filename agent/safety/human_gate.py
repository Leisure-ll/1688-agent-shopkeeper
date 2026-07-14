from dataclasses import dataclass


@dataclass
class HumanGateDecision:
    approved: bool
    reason: str = ""


class HumanGate:
    def wait_for_human(self, reason: str, prompt: str) -> HumanGateDecision:
        raise NotImplementedError


class AutoApproveGate(HumanGate):
    def wait_for_human(self, reason: str, prompt: str) -> HumanGateDecision:
        return HumanGateDecision(True, f"auto-approved: {reason}")


class DenyGate(HumanGate):
    def wait_for_human(self, reason: str, prompt: str) -> HumanGateDecision:
        return HumanGateDecision(False, f"denied: {reason}")
