"""
Journal Management Data Models Module

This module contains Pydantic data models and utilities for managing academic journal submissions
and publications within a compound AI system for journal generation. It provides models for:

1. Request Models: Handle user input for various AI services (Gemini, Groq, Core, LaTeX)
2. Journal Metadata Models: Store and validate journal-related information
3. Utility Classes: Provide date formatting and business logic calculations

Key Classes:
    - GeminiRequest, GroqRequest, CoreRequest: LLM service request models
    - DateUtils: Date formatting and business day calculations
    - PulsusInputStr: Validates journal metadata on submission
    - PulsusOutputStr: Represents complete journal output with generated content
    - UpdateInputPartJournal: Allows partial updates to existing journal records
    - TranslatePage: Manages multi-language journal translation
    - ArticleItem: Represents individual article/research paper details

The module is designed to work with multiple journal templates (hilaris, alliedAcademy, omics)
and automatically calculates publication timeline dates based on journal brand.

Author: Journal System Development Team
Version: 1.0
"""

from Apps.library_import import (
    BaseModel,
    Field,
    EmailStr,
    AnyUrl,
    Annotated,
    Optional,
    List,
    Dict,
    BaseModel,
    Field,
    field_validator,
    computed_field,
    datetime,
)
from Apps.services.io_service import IOService
from Apps.template_configs import TemplateFactory


class GeminiRequest(BaseModel):
    """
    Request model for Google Gemini AI service queries.

    Used to send prompts to Google's Gemini API for processing journal-related
    queries such as content generation, summarization, or analysis.

    Attributes:
        prompt (str): The input text/query to be processed by Gemini AI.
                     Should contain specific instructions or questions about
                     journal content.

    Example:
        >>> request = GeminiRequest(prompt="Generate an abstract for a research paper")
        >>> # Send to Gemini API for processing
    """

    prompt: str = Field(
        ...,
        title="Here, we can use Gemini",
        description="Enter prompt for the Gemini to compute....",
    )


class GroqRequest(BaseModel):
    """
    Request model for Groq AI service queries.

    Used to send prompts to Groq's API for high-speed AI inference tasks,
    particularly useful for journal processing and content generation.

    Attributes:
        prompt (str): The input text/query to be processed by Groq.
                     Can include journal content processing instructions.

    Example:
        >>> request = GroqRequest(prompt="Summarize this journal introduction")
        >>> # Send to Groq API for processing
    """

    prompt: str = Field(
        ...,
        title="Here, we can use Groq",
        description="Enter prompt for the Groq to compute....",
    )


class CoreRequest(BaseModel):
    """
    Request model for Core research API queries.

    Interfaces with the Core API to fetch research paper metadata and information
    for journal-related research page generation.

    Attributes:
        prompt (str): Search query or instruction for the Core API.
                     Used to fetch research papers and academic articles.

    Example:
        >>> request = CoreRequest(prompt="Find papers on machine learning")
        >>> # Query Core API for research papers
    """

    prompt: str = Field(
        ...,
        title="Here, we can use Core for Research pages",
        description="Enter prompt for the Core to compute....",
    )


class LatexRequest(BaseModel):
    """
    Request model for LaTeX document processing.

    Used to validate and process LaTeX source code for PDF generation
    and document formatting.

    Attributes:
        source (str): Raw LaTeX source code to be processed and compiled
                     into a PDF or other document format.

    Example:
        >>> request = LatexRequest(source=r"\\documentclass{article}...")
        >>> # Process for PDF generation
    """

    source: str


class DateUtils:
    """
    Utility class for date formatting.

    Business-day calculations are now fully delegated to each brand's template class
    via ``template.add_business_days(start_date, days)``.  Every template in
    ``Apps/template_configs/`` owns its own date logic so that it can be changed
    per-brand without touching this file.

    Notes:
        - All dates are expected in datetime.date format
        - Output dates are formatted as DD-Mon-YYYY (e.g., 15-Jan-2024)

    Example:
        >>> formatted = DateUtils.format_date(datetime.date(2024, 1, 15))
        >>> # '15-Jan-2024'
    """

    @staticmethod
    def format_date(date_obj: datetime.date) -> str:
        """
        Format a date object into DD-Mon-YYYY string format.

        Converts Python date objects to a readable string format commonly used
        in academic journal submissions (e.g., "15-Jan-2024").

        Args:
            date_obj (datetime.date): The date object to format.

        Returns:
            str: Formatted date string in DD-Mon-YYYY format.

        Example:
            >>> from datetime import date
            >>> d = date(2024, 1, 15)
            >>> DateUtils.format_date(d)
            '15-Jan-2024'
        """
        return date_obj.strftime("%d-%b-%Y")


class PulsusInputStr(BaseModel):
    """
    Input validation model for journal submission data.

    Represents the complete metadata for a new journal submission. This model validates
    all required information before a journal entry is created in the database.

    The model automatically calculates key workflow dates (editorAssigned, reviewed, revised,
    published) based on the received date and journal brand using the DateUtils class.

    Journal Brands Supported:
        - alliedAcademy.tex: Allied Academy journal template
        - hilaris.tex: Hilaris journal template
        - omics.tex: OMICS journal template

    Attributes:
        id (str): Unique identifier for the journal entry (3-6 characters).
        topic (str): Research topic title.
        journalName (str): Full name of the journal publication.
        shortJournalName (str): Abbreviated journal name (for citations).
        type (str): Journal article type (e.g., "Research Article", "Review", "Case Report").
        author (str): Full name of the primary/corresponding author (must contain first and last name).
        email (EmailStr): Valid email address of the corresponding author.
        brandName (str): Journal template/brand name (determines layout and formatting).
        authorsDepartment (str): Department affiliation of the author.
        received (str): Submission date in YYYY-MM-DD format.
        manuscriptNo (str): Unique manuscript identifier.
        volume (int): Journal volume number (must be > 0).
        issues (int): Issue number within the volume (must be > 0).
        pdfNo (int): Page or PDF number (must be > 0).
        doi (Optional[str]): Digital Object Identifier if available.
        ISSN (Optional[str]): International Standard Serial Number of the journal.
        imgPath (Optional[str]): Path to associated image file.
        parentLink (AnyUrl): URL link to the centralized journal page.
        editorAssigned (Optional[str]): Auto-calculated date when editor is assigned.
        reviewed (Optional[str]): Auto-calculated date when review is completed.
        revised (Optional[str]): Auto-calculated date when revision is completed.
        published (Optional[str]): Auto-calculated publication date.

    Validation:
        - Author must have at least first name and last name (space-separated)
        - All dates are formatted as DD-Mon-YYYY after model initialization
        - Dates are auto-calculated using business day logic specific to each brand

    Example:
        >>> data = {
        ...     "id": "test1",
        ...     "topic": "Machine Learning Applications",
        ...     "journalName": "Journal of AI Research",
        ...     "shortJournalName": "JAI",
        ...     "type": "Research Article",
        ...     "author": "John Smith",
        ...     "email": "john@example.com",
        ...     "brandName": "alliedAcademy.tex",
        ...     "authorsDepartment": "Computer Science",
        ...     "received": "2024-01-15",
        ...     "manuscriptNo": "2024-001",
        ...     "volume": 5,
        ...     "issues": 2,
        ...     "pdfNo": 45,
        ...     "parentLink": "https://journal.example.com"
        ... }
        >>> journal = PulsusInputStr(**data)
        >>> print(journal.editorAssigned)  # Auto-calculated date
    """

    id: Annotated[
        str,
        Field(
            ...,
            title="ID of the Input Journal",
            description="Enter the id for this journal input....",
            max_length=6,
            min_length=3,
        ),
    ]
    topic: Annotated[
        str, Field(..., title="Name of the topic", description="Enter the topic....")
    ]
    journalName: Annotated[
        str,
        Field(
            ...,
            title="Name of the journal where it belongs to.",
            description="Enter the journal where it belongs from...",
        ),
    ]
    shortJournalName: Annotated[
        str,
        Field(
            ...,
            title="Name of the short journal name where it belongs to.",
            description="Enter the short journal name where it belongs from...",
        ),
    ]
    type: Annotated[
        str,
        Field(
            ...,
            title="Name of the type(journal)",
            description="Enter the type of journal....",
        ),
    ]
    author: Annotated[
        str, Field(..., title="Name of the author", description="Enter the author....")
    ]
    email: Annotated[
        EmailStr,
        Field(
            ..., title="Email of the author", description="Enter the autors email...."
        ),
    ]
    brandName: Annotated[
        str,
        Field(
            ...,
            title="Name of the brand",
            description="Enter the name of your brand...",
        ),
    ]
    authorsDepartment: Annotated[
        str,
        Field(
            ...,
            title="Department of the authour",
            description="Enter the department of the author....",
        ),
    ]
    received: Annotated[
        str,
        Field(
            ...,
            title="The receiving date",
            description="Enter the receiving date in DD-Mon format....",
        ),
    ]
    manuscriptNo: Annotated[
        str,
        Field(
            ...,
            title="The manuscriptNo of this journal",
            description="Enter the manuscriptNo for this journal....",
        ),
    ]
    volume: Annotated[
        int,
        Field(
            ...,
            title="The volume for the issue",
            description="Enter the Volume of the issue...",
            gt=0,
        ),
    ]
    issues: Annotated[
        int,
        Field(
            ...,
            title="The issue no. of the volume",
            description="Enter the issue no. of the volume...",
            gt=0,
        ),
    ]
    pdfNo: Annotated[
        int,
        Field(
            ..., title="The pdf number", description="Enter the pdf number....", gt=0
        ),
    ]
    issueType: Annotated[
        Optional[str],
        Field(
            default="Issue",
            title="Issue Type",
            description="Select 'Issue' or 'Special Issue'. Only applies to ABAcademies brand.",
        ),
    ]
    doi: Annotated[
        Optional[str],
        Field(
            default="",
            title="DOI for this journal",
            description="Enter DOI for this Journal....",
        ),
    ]
    ISSN: Annotated[
        Optional[str],
        Field(
            default=None,
            title="ISSN number of this journal",
            description="Enter the ISSN number for the journal....",
        ),
    ]
    imgPath: Annotated[
        Optional[str],
        Field(default=None, title="image path", description="Enter the img path...."),
    ]
    parentLink: Annotated[
        AnyUrl,
        Field(
            ...,
            title="The url for the centralized link",
            description="Enter the link which will led to the centralized page....",
        ),
    ]

    editorAssigned: Optional[str] = None
    reviewed: Optional[str] = None
    revised: Optional[str] = None
    published: Optional[str] = None

    # Auto-populate extra dates after model init
    def model_post_init(self, __context):
        """
        Auto-calculate workflow dates after model initialization.

        Delegates all date-interval and business-day logic to the
        TemplateFactory so brand-specific rules live in one place.

        Side effects:
            - Modifies self.editorAssigned, self.reviewed, self.revised, self.published
            - Reformats self.received to DD-Mon-YYYY format
        """
        template = TemplateFactory.get(self.brandName)
        d = template.date_intervals          # [editor_assign, review, revise, publish]

        # Parse the received date from YYYY-MM-DD format
        received_date = datetime.datetime.strptime(self.received, "%Y-%m-%d").date()

        # Calculate and format each workflow date via the template's business-day logic
        self.editorAssigned = DateUtils.format_date(
            template.add_business_days(received_date, d[0])
        )
        self.reviewed = DateUtils.format_date(
            template.add_business_days(received_date, d[0] + d[1])
        )
        self.revised = DateUtils.format_date(
            template.add_business_days(received_date, d[0] + d[1] + d[2])
        )
        self.published = DateUtils.format_date(
            template.add_business_days(received_date, d[0] + d[1] + d[2] + d[3])
        )
        self.received = DateUtils.format_date(received_date)

    @computed_field
    @property
    def citeAuthorFormate(self) -> str:
        """Returns the LLM citation format prompt for this brand — delegated to the template config."""
        return TemplateFactory.get(self.brandName).get_citation_format_prompt()

    @field_validator("author")
    @classmethod
    def validateAuthor(cls, value):
        value = value.strip()
        if len(value.split(" ")) > 1:
            return value
        else:
            raise ValueError(
                {
                    "Message": "Author name must contain at least first name and last name."
                }
            )


class UpdateInputPartJournal(BaseModel):
    """
    Partial update model for existing journal records.

    This model allows updating selected fields of an already-created journal entry
    without requiring all fields to be provided. All fields are optional, enabling
    partial updates of journal metadata.

    Unlike PulsusInputStr which requires complete journal metadata, this model
    is designed for updating one or more fields of an existing journal record.

    Attributes:
        id (Optional[str]): Unique identifier of the journal to update.
        topic (Optional[str]): Research topic title.
        journalName (Optional[str]): Full journal name.
        shortJournalName (Optional[str]): Abbreviated journal name.
        type (Optional[str]): Journal article type.
        author (Optional[str]): Author's full name.
        email (Optional[EmailStr]): Author's email address.
        brandName (Optional[str]): Journal template/brand name.
        authorsDepartment (Optional[str]): Author's department.
        received (Optional[str]): Submission date.
        editorAssigned (Optional[str]): Editor assignment date.
        reviewed (Optional[str]): Review completion date.
        revised (Optional[str]): Revision completion date.
        published (Optional[str]): Publication date.
        manuscriptNo (Optional[str]): Manuscript identifier.
        volume (Optional[int]): Journal volume number.
        issues (Optional[int]): Issue number within volume.
        pdfNo (Optional[int]): Page or PDF number.
        doi (Optional[str]): Digital Object Identifier.
        ISSN (Optional[str]): International Standard Serial Number.
        imgPath (Optional[str]): Path to associated image.
        parentLink (Optional[AnyUrl]): URL to centralized journal page.

    Usage:
        Use this model when you need to update only specific fields of an existing
        journal record. Fields that are not provided (None) will not be updated.

    Example:
        >>> update_data = {
        ...     "id": "test1",
        ...     "topic": "Updated Topic",
        ...     "volume": 6
        ... }
        >>> journal_update = UpdateInputPartJournal(**update_data)
        >>> # Only these fields are updated in the database
    """

    id: Annotated[
        Optional[str],
        Field(
            default=None,
            title="ID of the Input Journal",
            description="Enter the id for this journal input....",
        ),
    ]
    topic: Annotated[
        Optional[str],
        Field(
            default=None, title="Name of the topic", description="Enter the topic...."
        ),
    ]
    journalName: Annotated[
        Optional[str],
        Field(
            default=None,
            title="Name of the journal where it belongs to.",
            description="Enter the journal where it belongs from...",
        ),
    ]
    shortJournalName: Annotated[
        Optional[str],
        Field(
            default=None,
            title="Name of the short journal name where it belongs to.",
            description="Enter the short journal name where it belongs from...",
        ),
    ]
    type: Annotated[
        Optional[str],
        Field(
            default=None,
            title="Name of the type(journal)",
            description="Enter the type of journal....",
        ),
    ]
    author: Annotated[
        Optional[str],
        Field(
            default=None, title="Name of the author", description="Enter the author...."
        ),
    ]
    email: Annotated[
        Optional[EmailStr],
        Field(
            default=None,
            title="Email of the author",
            description="Enter the autors email....",
        ),
    ]
    brandName: Annotated[
        Optional[str],
        Field(
            default=None,
            title="Name of the brand",
            description="Enter the name of your brand...",
        ),
    ]
    authorsDepartment: Annotated[
        Optional[str],
        Field(
            default=None,
            title="Department of the authour",
            description="Enter the department of the author....",
        ),
    ]
    received: Annotated[
        Optional[str],
        Field(
            default=None,
            title="The receiving date",
            description="Enter the receiving date in DD-Mon format....",
        ),
    ]
    editorAssigned: Annotated[
        Optional[str],
        Field(
            default=None,
            title="The Editor Assigned date",
            description="Enter the editor assigned date in DD-Mon format....",
        ),
    ]
    reviewed: Annotated[
        Optional[str],
        Field(
            default=None,
            title="The journal review date",
            description="Enter the journal review date in DD-Mon format....",
        ),
    ]
    revised: Annotated[
        Optional[str],
        Field(
            default=None,
            title="The journal revised date",
            description="Enter the journal revised date in DD-Mon format....",
        ),
    ]
    published: Annotated[
        Optional[str],
        Field(
            default=None,
            title="The publishing date of journal",
            description="Enter the publishing date of the journal in DD-Mon format....",
        ),
    ]
    manuscriptNo: Annotated[
        Optional[str],
        Field(
            default=None,
            title="The manuscriptNo of this journal",
            description="Enter the manuscriptNo for this journal....",
        ),
    ]
    volume: Annotated[
        Optional[int],
        Field(
            default=None,
            title="The volume for the issue",
            description="Enter the Volume of the issue...",
            gt=0,
        ),
    ]
    issues: Annotated[
        Optional[int],
        Field(
            default=None,
            title="The issue no. of the volume",
            description="Enter the issue no. of the volume...",
            gt=0,
        ),
    ]
    pdfNo: Annotated[
        Optional[int],
        Field(
            default=None,
            title="The pdf number",
            description="Enter the pdf number....",
            gt=0,
        ),
    ]
    issueType: Annotated[
        Optional[str],
        Field(
            default=None,
            title="Issue Type",
            description="Select 'Issue' or 'Special Issue'. Only applies to ABAcademies brand.",
        ),
    ]
    doi: Annotated[
        Optional[str],
        Field(
            default=None,
            title="DOI for this journal",
            description="Enter DOI for this Journal....",
        ),
    ]
    ISSN: Annotated[
        Optional[str],
        Field(
            default=None,
            title="ISSN number of this journal",
            description="Enter the ISSN number for the journal....",
        ),
    ]
    imgPath: Annotated[
        Optional[str],
        Field(default=None, title="image path", description="Enter the img path...."),
    ]
    parentLink: Annotated[
        Optional[AnyUrl],
        Field(
            default=None,
            title="The url for the centralized link",
            description="Enter the link which will led to the centralized page....",
        ),
    ]


class TranslatePage(BaseModel):
    """
    Model for managing multi-language journal page translation.

    Represents a request to translate a specific journal page into a different language.
    This is used in the translation pipeline to support internationalization of journals.

    Attributes:
        id (str): Unique identifier of the journal page to translate (3-6 characters).
                  Should match an existing journal entry's ID.
        language (str): Target language code or name for translation.
                       Examples: "Spanish", "French", "German", "es", "fr", "de"

    Notes:
        - The language field determines which language the page will be translated to
        - The source language is typically assumed to be the journal's original language
        - Translated content is typically stored separately with language prefixes

    Example:
        >>> translation = TranslatePage(id="test1", language="Spanish")
        >>> # This triggers translation of journal test1 to Spanish
    """

    id: Annotated[
        str,
        Field(
            ...,
            title="The id of the page",
            description="Enter the id of the page....",
            min_length=3,
            max_length=6,
        ),
    ]
    language: Annotated[
        str,
        Field(
            default=None,
            title="The language of the page",
            description="Enter the language of the page....",
        ),
    ]


class ArticleItem(BaseModel):
    """
    Model representing a single article or research paper metadata.

    Captures metadata about a research article sourced from external APIs (like Core API)
    or extracted from bibliographic databases. This is used to populate journal contents
    with article references and metadata.

    All fields are optional to accommodate varying levels of metadata availability
    from different sources.

    Attributes:
        title (Optional[str]): Full title of the research article or paper.
        subContent (Optional[str]): Subtitle, alternative title, or summary of content.
        authors (Optional[str]): Author names, typically comma-separated.
        published (Optional[str]): Publication date in string format.
        doi (Optional[str]): Digital Object Identifier of the article.
        url (Optional[AnyUrl]): Direct URL/link to the article online.
        fulltextLinks (Optional[List[str]]): List of URLs to full-text versions of the article.
        keywords (Optional[str]): Relevant keywords describing the article's content.
        references (Optional[str]): Bibliographic references cited in the article.

    Usage:
        Used to store article metadata fetched from research APIs or when populating
        journal content with references to other research papers.

    Example:
        >>> article = ArticleItem(
        ...     title="Machine Learning in Healthcare",
        ...     authors="John Smith, Jane Doe",
        ...     published="2023-05-15",
        ...     doi="10.1234/example",
        ...     url="https://example.com/article"
        ... )
    """

    title: Annotated[
        Optional[str],
        Field(
            default=None, title="Name of the topic", description="Enter the topic...."
        ),
    ]
    subContent: Annotated[
        Optional[str],
        Field(
            default=None, title="Name of the topic", description="Enter the topic...."
        ),
    ]
    authors: Annotated[
        Optional[str],
        Field(
            default=None, title="Name of the topic", description="Enter the topic...."
        ),
    ]
    published: Annotated[
        Optional[str],
        Field(
            default=None, title="Name of the topic", description="Enter the topic...."
        ),
    ]
    doi: Annotated[
        Optional[str],
        Field(
            default=None, title="Name of the topic", description="Enter the topic...."
        ),
    ]
    url: Annotated[
        Optional[AnyUrl],
        Field(
            default=None, title="Name of the topic", description="Enter the topic...."
        ),
    ]
    fulltextLinks: Annotated[
        Optional[List[str]],
        Field(
            default=None, title="Name of the topic", description="Enter the topic...."
        ),
    ]
    keywords: Annotated[
        Optional[str],
        Field(
            default=None, title="Name of the topic", description="Enter the topic...."
        ),
    ]
    references: Annotated[
        Optional[str],
        Field(
            default=None, title="Name of the topic", description="Enter the topic...."
        ),
    ]


class PulsusOutputStr(BaseModel):
    """
    Complete journal output model with all generated content.

    Represents a fully processed journal article with all metadata, content sections,
    and AI-generated text. This model is used to store and output the complete
    journal record after all processing steps (metadata entry, AI generation,
    content assembly, etc.) are complete.

    This is the final output format that contains everything needed for:
    - PDF generation (with LaTeX templates)
    - Web display
    - Database storage
    - Citation generation
    - Multi-language translation

    The model includes computed fields that automatically generate formatted content
    such as proper citations based on journal brand, author formatting for copyright,
    and correspondence formatting.

    Attributes:
        title (str): Full title of the research article.
        journalName (str): Complete journal name.
        shortJournalName (str): Abbreviated journal name for citations.
        type (str): Article type (Research Article, Review, Case Report, etc.).
        author (str): Primary/corresponding author's full name.
        email (EmailStr): Author's email address.
        brandName (str): Journal brand/template name.
        authorsDepartment (str): Author's affiliated department.
        journalYearVolumeIssue (str): Publication details (year, volume, issue).
        introduction (str): Introduction section of the article.
        description (str): Brief description/summary of the article.
        content (Dict[str, Dict]): Main content sections (methods, results, etc.).
        abstract (str): Concise summary of the research.
        discussion (str): Discussion of findings and implications.
        keywords (str): Relevant keywords for the article.
        doi (Optional[str]): Digital Object Identifier.
        received (str): Manuscript submission date.
        editorAssigned (str): Editor assignment date.
        reviewed (str): Review completion date.
        revised (str): Revision completion date.
        published (str): Publication/release date.
        year (int): Publication year.
        month (str): Publication month.
        manuscriptNo (str): Unique manuscript number.
        QCNo (str): Quality control number.
        preQCNo (str): Pre-quality control number.
        RManuNo (str): Revised manuscript number.
        volume (str): Journal volume number.
        issues (str): Issue number.
        ISSN (Optional[str]): International Standard Serial Number.
        imgPath (Optional[str]): Path to associated images.
        pdfNo (int): PDF or page number.
        parentLink (AnyUrl): URL to centralized journal page.
        conclusion (str): Conclusion section of the article.

    Computed Fields (Auto-generated):
        - firstNameAuthor: Extracts first name from author field
        - copyrightAuthor: Formats author name for copyright statement
        - addressForCorres: Formats author name for correspondence address
        - citation: Generates proper citation based on journal brand format

    Example:
        >>> journal_output = PulsusOutputStr(
        ...     title="Advanced ML Applications",
        ...     author="John Smith",
        ...     brandName="alliedAcademy.tex",
        ...     # ... many more fields ...
        ... )
        >>> citation = journal_output.citation  # Auto-generated formatted citation
    """

    title: Annotated[
        str,
        Field(
            ...,
            title="Article Title",
            description="The full title of the research paper or article.",
        ),
    ]
    journalName: Annotated[
        str,
        Field(
            ...,
            title="Journal Name",
            description="Enter the journal name where it belongs from.",
        ),
    ]
    shortJournalName: Annotated[
        str,
        Field(
            ...,
            title="Short Journal Name",
            description="The abbreviated or short form of the journal’s name.",
        ),
    ]
    type: Annotated[
        str,
        Field(
            ...,
            title="Journal Type",
            description="The category of the paper (Eg-Peer reviewed,Research Article, Review, Case Report, etc.)",
        ),
    ]
    author: Annotated[
        str,
        Field(
            ...,
            title="Author Name",
            description="Name of the primary author or corresponding author.",
        ),
    ]
    email: Annotated[
        EmailStr,
        Field(
            ...,
            title="Author Email",
            description="Official email address of the corresponding author.",
        ),
    ]
    brandName: Annotated[
        str,
        Field(
            ...,
            title="Publisher Brand Name",
            description="The brand or publishing house responsible for the journal.",
        ),
    ]
    authorsDepartment: Annotated[
        str,
        Field(
            ...,
            title="Author’s Department",
            description="The department to which the author is affiliated with.",
        ),
    ]
    journalYearVolumeIssue: Annotated[
        str,
        Field(
            ...,
            title="Year, Volume & Issue",
            description="The publication details in the format: Year, Volume, and Issue.",
        ),
    ]
    introduction: Annotated[
        str,
        Field(
            ...,
            title="Introduction",
            description="The introductory section outlining background and objectives of the study.",
        ),
    ]
    description: Annotated[
        str,
        Field(
            ...,
            title="Journal Description",
            description="A brief summary or narrative about the article’s content.",
        ),
    ]
    content: Annotated[
        Dict[str, Dict],
        Field(
            ...,
            title="Journal Content",
            description="Enter the id for this journal input....",
        ),
    ]
    abstract: Annotated[
        str,
        Field(
            ...,
            title="Abstract of the Journal",
            description="A concise summary of the research purpose, methods, results, and conclusion.",
        ),
    ]
    discussion: Annotated[
        str,
        Field(
            ...,
            title="Discussion",
            description="Section discussing the findings, interpretations, and implications.",
        ),
    ]
    keywords: Annotated[
        str,
        Field(
            ...,
            title="Keywords",
            description="Relevant keywords that describe the main topics of the paper.",
        ),
    ]
    doi: Annotated[
        Optional[str],
        Field(
            default=None,
            title="DOI (Digital Object Identifier)",
            description="The unique DOI assigned to the article, if available.",
        ),
    ]
    received: Annotated[
        str,
        Field(
            ...,
            title="Date Received",
            description="The date when the manuscript was initially received by the journal.",
        ),
    ]
    editorAssigned: Annotated[
        str,
        Field(
            ...,
            title="ID of the Input Journal",
            description="Enter the id for this journal input....",
        ),
    ]
    reviewed: Annotated[
        str,
        Field(
            ...,
            title="ID of the Input Journal",
            description="Enter the id for this journal input....",
        ),
    ]
    revised: Annotated[
        str,
        Field(
            ...,
            title="ID of the Input Journal",
            description="Enter the id for this journal input....",
        ),
    ]
    published: Annotated[
        str,
        Field(
            ...,
            title="ID of the Input Journal",
            description="Enter the id for this journal input....",
        ),
    ]
    year: Annotated[
        int,
        Field(
            ...,
            title="year of publishing",
            description="Enter the journal publising year...",
        ),
    ]
    month: Annotated[
        str,
        Field(
            ...,
            title="Month of publishing",
            description="Enter the journal publising month...",
        ),
    ]
    manuscriptNo: Annotated[
        str,
        Field(
            ...,
            title="ID of the Input Journal",
            description="Enter the id for this journal input....",
        ),
    ]
    QCNo: Annotated[
        str, Field(..., title="The QC number", description="Enter the QC number....")
    ]
    preQCNo: Annotated[
        str,
        Field(..., title="The preQC number", description="Enter the preQC number...."),
    ]
    RManuNo: Annotated[
        str,
        Field(
            ..., title="The RManuNo number", description="Enter the RManuNo number...."
        ),
    ]
    volume: Annotated[
        str,
        Field(
            ...,
            title="The volume for the issue",
            description="Enter the Volume of the issue...",
        ),
    ]
    issues: Annotated[
        str,
        Field(
            ...,
            title="The issue no. of the volume",
            description="Enter the issue no. of the volume...",
        ),
    ]
    issueType: Annotated[
        Optional[str],
        Field(
            default="Issue",
            title="Issue Type",
            description="'Issue' or 'Special Issue'. Only applies to ABAcademies brand.",
        ),
    ]
    ISSN: Annotated[
        Optional[str],
        Field(default="", title="ISSN Number", description="Enter the ISSN Number...."),
    ]
    imgPath: Annotated[
        Optional[str],
        Field(default=None, title="image path", description="Enter the img path...."),
    ]
    pdfNo: Annotated[
        int, Field(..., title="Pdf Number", description="Enter the PDF Number....")
    ]
    parentLink: Annotated[
        AnyUrl,
        Field(
            ...,
            title="ID of the Input Journal",
            description="Enter the id for this journal input....",
        ),
    ]
    conclusion: Annotated[
        str,
        Field(
            ...,
            title="ID of the Input Journal",
            description="Enter the id for this journal input....",
        ),
    ]

    @computed_field
    @property
    def firstNameAuthor(self) -> str:
        """
        Extract the first name from the author field.

        Returns the first word of the author's full name, typically the given/first name.

        Returns:
            str: The first name of the author (first word before space).

        Example:
            >>> output.author = "John Michael Smith"
            >>> output.firstNameAuthor
            'John'
        """
        copyAuth = self.author.split(" ")
        return copyAuth[0]

    # @field_validator("content")
    # @classmethod
    # def validatePDFNo(cls, value):
    #     # Avoid modifying dict during iteration
    #     keys_to_delete = []
    #     for i, j in value.items():
    #         if j.get("subContent") is None or j.get("references") is None:
    #             keys_to_delete.append(i)
    #     for k in keys_to_delete:
    #         del value[k]
    #     return value

    @computed_field
    @property
    def copyrightAuthor(self) -> str:
        """
        Format author name for copyright statements.

        Converts author name to copyright format: "LastName FirstInitial."
        This format is commonly used in copyright statements and legal documents.

        Returns:
            str: Formatted name as "LastName FirstInitial." (e.g., "Smith J.")

        Example:
            >>> output.author = "John Michael Smith"
            >>> output.copyrightAuthor
            'Smith J.'
        """
        copyAuth = self.author.split(" ")
        copyAuth = copyAuth[::-1]  # Reverse to get last name first
        copyAuth[1] = f"{copyAuth[1][0]}."  # Convert to initial
        return " ".join(copyAuth)

    @computed_field
    @property
    def addressForCorres(self) -> str:
        """
        Format author name for correspondence address display.

        Adds a comma after the first name, commonly used in address blocks
        and correspondence sections of academic documents.

        Returns:
            str: Author name with comma after first name (e.g., "John, Michael Smith")

        Example:
            >>> output.author = "John Michael Smith"
            >>> output.addressForCorres
            'John, Michael Smith'
        """
        copyAuth = self.author.split(" ")
        copyAuth[0] = f"{copyAuth[0]},"  # Add comma after first name
        return " ".join(copyAuth)

    @computed_field
    @property
    def citation(self) -> str:
        """
        Generate a properly formatted citation for this journal article.

        Delegates to the brand-specific template so that citation style
        is defined in one place (Apps/template_configs/<brand>.py).

        Returns:
            str: Fully formatted citation ready for bibliographies and references.
        """
        return TemplateFactory.get(self.brandName).format_output_citation(
            author=self.author,
            title=self.title,
            short_journal=self.shortJournalName,
            volume=self.volume,
            issues=self.issues,
            published=self.published,
            pdf_no=self.pdfNo,
        )
