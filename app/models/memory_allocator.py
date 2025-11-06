from sqlalchemy import Column, Integer, String, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from app.db.database import Base


class TestCase(Base):
    __tablename__ = "tests"

    id = Column(Integer, primary_key=True)
    modules = relationship("Module", back_populates="test")


class Module(Base):
    """
    Model of Memory Module.
    """
    __tablename__ = "modules"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False, index=True)
    address_space_base = Column(Integer, nullable=True)
    kernel_blocks = relationship("Block", back_populates="module")
    partitions = relationship("Partition", back_populates="module")
    test = relationship("TestCase", back_populates="modules")
    test_id = Column(Integer, ForeignKey("tests.id"), nullable=False)


class Partition(Base):
    """
    Model of Module Partition.
    """
    __tablename__ = "partitions"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False, index=True)
    space_id = Column(Integer, nullable=False, index=True)
    module_id = Column(Integer, ForeignKey("modules.id"))
    module = relationship("Module", back_populates="partitions")
    blocks = relationship("Block", back_populates="partition")


class Block(Base):
    """
    Model of Memory Block.
    """
    __tablename__ = "blocks"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False, index=True)
    access = Column(String, nullable=False)
    align = Column(String, nullable=False)
    cache_policy = Column(String, nullable=False)
    content_type = Column(String)
    init_file = Column(String)
    init_stage = Column(String)
    init_type = Column(String)
    is_contiguous = Column(Boolean, nullable=False)
    is_shadow = Column(Boolean, nullable=False)
    is_shareable = Column(Boolean, nullable=False)
    is_system = Column(Boolean, nullable=False)
    no_shadow = Column(Boolean, nullable=False)
    paddr = Column(Integer)
    size = Column(Integer)
    vaddr = Column(Integer, nullable=False)
    shadow_offset = Column(Integer)
    shadow_scale = Column(Integer)
    shadow_type = Column(String)
    safety_zone_before = Column(String)
    safety_zone_after = Column(String)

    module_id = Column(Integer, ForeignKey("modules.id"), nullable=False)
    partition_id = Column(Integer, ForeignKey("partitions.id"), nullable=False)

    module = relationship("Module", back_populates="kernel_blocks")
    partition = relationship("Partition", back_populates="blocks")
    regions = relationship("Region", back_populates="block")


class Region(Base):
    """
    Model of Block Region.
    """
    __tablename__ = "regions"
    id = Column(Integer, primary_key=True)
    block = relationship("Block", back_populates="regions")
    paddr = Column(Integer, nullable=False)
    size = Column(Integer, nullable=False)
    vaddr = Column(Integer, nullable=False)
