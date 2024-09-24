import datetime
import enum
from sqlalchemy import Boolean, Column, DateTime, Enum, Float, ForeignKey, Integer, LargeBinary, String, TIMESTAMP
from sqlalchemy.orm import relationship

from .database import Base

class PlantStatus(str, enum.Enum):
    active = "active"
    inactive = "inactive"

class Plant(Base):
    __tablename__ = "plants"

    id = Column(Integer, primary_key=True)
    name = Column(String(100))
    description = Column(String(100))
    address = Column(String(100))
    plantConfidence = Column(Float)
    plantstatus = Column(Enum(PlantStatus), default=PlantStatus.inactive, nullable=False)

    zones = relationship("Zone", back_populates="plant")


class Assignee(Base):
    __tablename__ = "assignees"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), index=True)
    email = Column(String(100))
    phone = Column(String(100))
    
    assignee = relationship("Zone", back_populates="assignees")

class RecordingScenario(Base):
    __tablename__ = "recording_scenarios"

    id = Column(Integer, primary_key=True)
    recording_id = Column(Integer)
    scenario_id = Column(Integer)


class Zone(Base):
    __tablename__ = "zones"

    id = Column(Integer, primary_key=True)
    title = Column(String(100), index=True)
    description = Column(String(100))
    zoneconfidence = Column(Float)
    plant_id = Column(Integer, ForeignKey("plants.id"))
    zonestatus = Column(Enum(PlantStatus), default=PlantStatus.active, nullable=False)
    assignee_id = Column(Integer, ForeignKey("assignees.id"))

    plant = relationship("Plant", back_populates="zones")
    cameras = relationship("Camera", back_populates="zone")
    assignees = relationship("Assignee", back_populates="assignee")


class Camera(Base):
    __tablename__ = "cameras"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), index=True)
    description = Column(String(100))
    ipaddress = Column(String(100))
    zone_id = Column(Integer, ForeignKey("zones.id"))

    zone = relationship("Zone", back_populates="cameras")
    recordings = relationship("Recording", back_populates="camera")


class Recording(Base):
    __tablename__ = "recordings"

    id = Column(Integer, primary_key=True)
    name = Column(String(256))
    starttime = Column(TIMESTAMP)
    endtime = Column(TIMESTAMP)
    status = Column(Boolean, unique=False, default=True)
    task_id = Column(String(256))
    zone_id = Column(Integer)
    confidence = Column(Integer)
    assignee_id = Column(Integer)
    camera_id = Column(Integer, ForeignKey("cameras.id"))
    detection_type_id = Column(Integer, ForeignKey("detectiontypes.id"))

    camera = relationship("Camera", back_populates="recordings")
    detectiontype = relationship("DetectionType", back_populates="recordings")
    incidents = relationship("Incident", back_populates="recording")


class Incident(Base):
    __tablename__ = "incidents"

    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    class_name = Column(String(256), index=True)
    confidence = Column(Float)
    bbox = Column(String(256))
    frame = Column(LargeBinary(length=(2**32)-1))
    recording_id = Column(Integer, ForeignKey("recordings.id"))

    recording = relationship("Recording", back_populates="incidents")


class Scenario(Base):
    __tablename__ = "scenarios"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), index=True)
    description = Column(String(100))

class DetectionType(Base):
    __tablename__ = "detectiontypes"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), index=True)
    description = Column(String(100))
    modelpath = Column(String(100))
    task_name = Column(String(100))

    recordings = relationship("Recording", back_populates="detectiontype")
    
