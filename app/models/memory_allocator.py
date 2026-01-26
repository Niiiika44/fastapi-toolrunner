from sqlalchemy import Enum, ForeignKey, Text, BigInteger
from sqlalchemy.orm import relationship, Mapped, mapped_column

from app.core.enums import TestStatus
from app.db.database import Base


class TestCase(Base):
    """
    Model of test case.
    """
    __tablename__ = "tests"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(nullable=False, index=True)
    status: Mapped[TestStatus] = mapped_column(Enum(TestStatus), default=TestStatus.PENDING, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text)

    modules: Mapped[list["Module"]] = relationship("Module", back_populates="test")


class Module(Base):
    """
    Model of memory module.
    """
    __tablename__ = "modules"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(nullable=False, index=True)
    address_space_base: Mapped[int | None] = mapped_column()

    test_id: Mapped[int] = mapped_column(ForeignKey("tests.id"), nullable=False)

    kernel_blocks: Mapped[list["Block"]] = relationship("Block", back_populates="module")
    partitions: Mapped[list["Partition"]] = relationship("Partition", back_populates="module")
    test: Mapped[list["TestCase"]] = relationship("TestCase", back_populates="modules")


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
    blocks: Mapped[list["Module"]] = relationship("Block", back_populates="partition")


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
    is_shareable: Mapped[bool] = mapped_column(nullable=False)
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
    regions: Mapped[list["Region"]] = relationship(back_populates="block")


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

    block = relationship("Block", back_populates="regions")
