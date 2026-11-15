# Import all models here so that:
# 1. SQLAlchemy's mapper registry is populated
# 2. Alembic autogenerate can detect all tables
# Phase 1 & 2 models
from app.models.project import ResearchProject  # noqa: F401
from app.models.run import ResearchRun  # noqa: F401
from app.models.document import UploadedDocument  # noqa: F401
from app.models.evidence import EvidenceRecord  # noqa: F401
from app.models.report import ResearchReport  # noqa: F401
# Phase 3 models — import order matters: plan before task before event
from app.models.plan import ResearchPlan  # noqa: F401
from app.models.task import ResearchTask  # noqa: F401
from app.models.event import AgentExecutionEvent  # noqa: F401
# Phase 4 models
from app.models.chunk import DocumentChunk  # noqa: F401
from app.models.source import Source  # noqa: F401
from app.models.claim import Claim  # noqa: F401
from app.models.claim_verification import ClaimVerification  # noqa: F401
from app.models.critic_review import CriticReview  # noqa: F401
from app.models.citation import Citation  # noqa: F401
# Phase 5 models
from app.models.approval import ApprovalRequest  # noqa: F401
from app.models.report_version import ReportVersion  # noqa: F401
from app.models.export_record import ExportRecord  # noqa: F401
