from pydantic import BaseModel, Field


class MDCResponse(BaseModel):
    """Model for structured MDC file content generation."""

    description: str = Field(
        ..., description="A brief description of what this rule provides context for."
    )
    globs: list[str] = Field(
        ..., description="File patterns this rule applies to, using glob syntax."
    )
    always_apply: bool = Field(
        ...,
        description="Whether this rule should always be applied regardless of file context. Generally this should be false other than core rules.",
    )
    content: str = Field(
        ...,
        description="The markdown content providing useful documentation and context.",
    )
