"""
Book Writer v2.0 Custom Exceptions
"""


class BookWriterError(Exception):
    """Base exception for Book Writer"""
    pass


class AgentError(BookWriterError):
    """Error in agent execution"""
    def __init__(self, agent_name: str, message: str, recoverable: bool = True):
        self.agent_name = agent_name
        self.recoverable = recoverable
        super().__init__(f"[{agent_name}] {message}")


class QualityGateFailedError(BookWriterError):
    """Quality gate check failed"""
    def __init__(self, issues: list, recommendations: list):
        self.issues = issues
        self.recommendations = recommendations
        super().__init__(f"Quality gate failed: {', '.join(issues[:3])}")


class ExpansionLimitError(BookWriterError):
    """Maximum expansion attempts reached"""
    def __init__(self, section_id: str, attempts: int):
        self.section_id = section_id
        self.attempts = attempts
        super().__init__(f"Section {section_id} reached max expansion attempts ({attempts})")


class StructureError(BookWriterError):
    """Invalid book structure"""
    pass


class ContentError(BookWriterError):
    """Content generation error"""
    pass


class OutputError(BookWriterError):
    """Output generation error"""
    pass
