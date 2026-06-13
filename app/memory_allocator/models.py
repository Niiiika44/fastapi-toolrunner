import datetime

from sqlalchemy import BigInteger, Column, Enum, ForeignKey, Table, Text, DateTime
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base
from app.memory_allocator.enums import ArtifactKind, TestStatus

test_case_tag = Table(
    "test_case_tag",
    Base.metadata,
    Column("test_id", ForeignKey("tests.id"), primary_key=True),
    Column("tag_id", ForeignKey("tags.id"), primary_key=True),
)


class Platform(Base):
    """
    Model of MMU Platform
    """
    __tablename__ = "platforms"

    id: Mapped[int] = mapped_column(primary_key=True)
    mmu_family: Mapped[str] = mapped_column(unique=True, nullable=False, index=True)
    page_size: Mapped[int] = mapped_column(nullable=False, default=8)
    config: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.datetime.now(datetime.UTC)
    )

    tests: Mapped[list["TestCase"]] = relationship("TestCase", back_populates="platform")

    def __str__(self):
        return f"Platform {self.mmu_family}"

    def __repr__(self):
        return str(self)


class Tag(Base):
    """
    Model of filtering tags
    """
    __tablename__ = "tags"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(unique=True,  nullable=False, index=True)
    tests: Mapped[list["TestCase"]] = relationship(
        secondary=test_case_tag, back_populates="tags"
    )

    def __str__(self):
        return f"Tag {self.name}"

    def __repr__(self):
        return str(self)


class ValidationResult(Base):
    """
    Model of validator and checker revisions
    """
    __tablename__ = "validation_results"

    id: Mapped[int] = mapped_column(primary_key=True)
    valid: Mapped[bool] = mapped_column(nullable=False, default=False)
    schema_valid: Mapped[bool] = mapped_column(nullable=False, default=False)
    errors: Mapped[list | None] = mapped_column(JSONB)
    checker_version: Mapped[str] = mapped_column(nullable=False)
    checked_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.datetime.now(datetime.UTC)
    )

    test_id: Mapped[int] = mapped_column(ForeignKey("tests.id"), nullable=False)
    test: Mapped["TestCase"] = relationship(back_populates="validations")

    def __str__(self):
        return f"Validator result is {self.schema_valid}, checker result is {self.valid}"

    def __repr__(self):
        return str(self)


class TestArtifact(Base):
    """
    Model of test aftifact
    """
    __tablename__ = "test_artifacts"

    id: Mapped[int] = mapped_column(primary_key=True)

    kind: Mapped[ArtifactKind] = mapped_column(Enum(ArtifactKind), nullable=False)
    filename: Mapped[str] = mapped_column(nullable=False)
    storage_key: Mapped[str] = mapped_column(nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.datetime.now(datetime.UTC)
    )

    test_id: Mapped[int] = mapped_column(ForeignKey("tests.id"), nullable=False)
    test: Mapped["TestCase"] = relationship(back_populates="artifacts")

    def __str__(self):
        return f"Artifact {self.filename} of test {self.test_id}"

    def __repr__(self):
        return str(self)


class TestCase(Base):
    """
    Model of test case.
    """
    __tablename__ = "tests"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(nullable=False, index=True)
    status: Mapped[TestStatus] = mapped_column(
        Enum(TestStatus),
        default=TestStatus.PENDING,
        nullable=False
    )
    error_message: Mapped[str | None] = mapped_column(Text)
    uploaded_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.datetime.now(datetime.UTC)
    )

    platform_id: Mapped[int] = mapped_column(ForeignKey("platforms.id"), nullable=False)

    modules: Mapped[list["Module"]] = relationship(
        "Module", back_populates="test", cascade="all, delete-orphan"
    )
    platform: Mapped["Platform"] = relationship(back_populates="tests")
    validations: Mapped[list["ValidationResult"]] = relationship(
        "ValidationResult", back_populates="test", cascade="all, delete-orphan"
    )
    artifacts: Mapped[list["TestArtifact"]] = relationship(
        "TestArtifact", back_populates="test", cascade="all, delete-orphan"
    )
    tags: Mapped[list["Tag"]] = relationship(
        secondary=test_case_tag, back_populates="tests"
    )

    # Filtering columns
    module_count: Mapped[int] = mapped_column(nullable=False, default=0)
    block_count: Mapped[int] = mapped_column(nullable=False, default=0)
    kernel_entry_count: Mapped[int] = mapped_column(nullable=False, default=0)
    user_entry_count: Mapped[int] = mapped_column(nullable=False, default=0)

    def __str__(self):
        return f"Test Case {self.name}_{self.status}"

    def __repr__(self):
        return str(self)


class Module(Base):
    """
    Model of memory module.
    """
    __tablename__ = "modules"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(nullable=False, index=True)
    address_space_base: Mapped[int | None] = mapped_column()

    test_id: Mapped[int] = mapped_column(ForeignKey("tests.id"), nullable=False)

    kernel_blocks: Mapped[list["Block"]] = relationship(
        "Block", back_populates="module", cascade="all, delete-orphan"
    )
    partitions: Mapped[list["Partition"]] = relationship(
        "Partition", back_populates="module", cascade="all, delete-orphan"
    )
    test: Mapped["TestCase"] = relationship("TestCase", back_populates="modules")

    def __str__(self):
        return f"Module {self.name}"

    def __repr__(self):
        return str(self)


class Partition(Base):
    """
    Model of module partition.
    """
    __tablename__ = "partitions"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(nullable=False, index=True)
    space_id: Mapped[int] = mapped_column(nullable=False, index=True)

    module_id: Mapped[int] = mapped_column(ForeignKey("modules.id"), nullable=False)

    module: Mapped["Module"] = relationship("Module", back_populates="partitions")
    blocks: Mapped[list["Block"]] = relationship("Block", back_populates="partition")

    def __str__(self):
        return f"Partition {self.name}_{self.space_id}"

    def __repr__(self):
        return str(self)


class Block(Base):
    """
    Model of memory block.
    """
    __tablename__ = "blocks"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(nullable=False, index=True)
    access: Mapped[str] = mapped_column(nullable=False)
    align: Mapped[int] = mapped_column(nullable=False)
    cache_policy: Mapped[str] = mapped_column(nullable=False)
    content_type: Mapped[str | None] = mapped_column()
    init_file: Mapped[str | None] = mapped_column()
    init_stage: Mapped[str | None] = mapped_column()
    init_type: Mapped[str | None] = mapped_column()
    is_contiguous: Mapped[bool] = mapped_column(nullable=False)
    is_shadow: Mapped[bool] = mapped_column(nullable=False)
    is_system: Mapped[bool] = mapped_column(nullable=False)
    no_shadow: Mapped[bool] = mapped_column(nullable=False)
    paddr: Mapped[int | None] = mapped_column(BigInteger)
    size: Mapped[int | None] = mapped_column(BigInteger)
    vaddr: Mapped[int] = mapped_column(BigInteger, nullable=False)
    shadow_offset: Mapped[int | None] = mapped_column()
    shadow_scale: Mapped[int | None] = mapped_column()
    shadow_type: Mapped[str | None] = mapped_column()
    safety_zone_before: Mapped[int] = mapped_column(nullable=False)
    safety_zone_after: Mapped[int] = mapped_column(nullable=False)
    safety_zone_before_unmapped: Mapped[bool] = mapped_column(nullable=False)
    safety_zone_after_unmapped: Mapped[bool] = mapped_column(nullable=False)

    module_id: Mapped[int] = mapped_column(ForeignKey("modules.id"), nullable=False)
    partition_id: Mapped[int | None] = mapped_column(ForeignKey("partitions.id"))

    module: Mapped["Module"] = relationship(back_populates="kernel_blocks")
    partition: Mapped["Partition"] = relationship(back_populates="blocks")
    regions: Mapped[list["Region"]] = relationship(
        back_populates="block", cascade="all, delete-orphan"
    )

    def __str__(self):
        return f"Block {self.name}"

    def __repr__(self):
        return str(self)


class Region(Base):
    """
    Model of block region.
    """
    __tablename__ = "regions"

    id: Mapped[int] = mapped_column(primary_key=True)
    paddr: Mapped[int] = mapped_column(nullable=False)
    size: Mapped[int] = mapped_column(nullable=False)
    vaddr: Mapped[int] = mapped_column(nullable=False)

    block_id: Mapped[int] = mapped_column(ForeignKey("blocks.id"), nullable=False)

    block: Mapped["Block"] = relationship(back_populates="regions")

    def __str__(self):
        return f"Region with vaddr {self.vaddr}"

    def __repr__(self):
        return str(self)
