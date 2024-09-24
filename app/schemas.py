import datetime
from enum import Enum
from typing import Dict, Optional
from pydantic import BaseModel


class DetectionTypeEnum(str, Enum):
    ppe = "ppe"
    pallet = "pallet"
    forklift = "forklift"

class PlantStatusEnum(str, Enum):
    active = "active"
    inactive = "inactive"

class Incident(BaseModel):
    id: int 
    timestamp: datetime.date
    class_name: str
    confidence: str
    bbox: str
    frame: str
    recording_id: int

    class Config:
        from_attributes = True
        populate_by_name = True
        arbitrary_types_allowed = True


class ReadRecording(BaseModel):
    id: int
    name: str
    zone_id: int
    assignee_id: int
    detection_type_id: int
    starttime: datetime.datetime
    endtime: Optional[datetime.datetime]
    status: bool
    confidence: Optional[int]
    task_id: Optional[str] 
    camera_id: int 

    class Config:
        from_attributes = True
        populate_by_name = True
        arbitrary_types_allowed = True

class CreateRecording(BaseModel):
    name: str
    zone_id: int
    assignee_id: int
    detection_type: int
    camera_id: int
    confidence: Optional[int]
    status: bool = True     
    class Config:
        from_attributes = True
        populate_by_name = True
        arbitrary_types_allowed = True


class Camera(BaseModel):
    id: int
    name: str
    description: str
    ipaddress: str
    zone_id: int
    recordings: list[ReadRecording] = []

    class Config:
        from_attributes = True
        populate_by_name = True
        arbitrary_types_allowed = True

class ReadCamera(BaseModel):
    id: int
    name: str
    description: str
    ipaddress: str
    zone_id: int
    recordings: list[ReadRecording] = []

    class Config:
        from_attributes = True
        populate_by_name = True
        arbitrary_types_allowed = True

class CreateCamera(BaseModel):
    name: str
    description: str
    ipaddress: str
    zone_id: int

    class Config:
        from_attributes = True
        populate_by_name = True
        arbitrary_types_allowed = True

class CreateZoneCamera(BaseModel):
    name: str
    description: str
    ipaddress: str
    class Config:
        from_attributes = True
        populate_by_name = True
        arbitrary_types_allowed = True
class ReadZone(BaseModel):
    id: int
    title: str
    description: str
    plant_id: int
    assignee_id: int
    zoneconfidence: Optional[float]
    zonestatus: PlantStatusEnum
    cameras: list[Camera] = []

    class Config:
        from_attributes = True
        populate_by_name = True
        arbitrary_types_allowed = True

class CreateZone(BaseModel):
    title: str
    description: str
    plant_id: int
    zoneconfidence: Optional[float]
    assignee_id: int
    cameras: list[CreateZoneCamera] = []

    class Config:
        from_attributes = True
        populate_by_name = True
        arbitrary_types_allowed = True


class UpdateZone(BaseModel):
    zoneconfidence: Optional[float]


class Scenario(BaseModel):
    id: int 
    name: str
    description: str 

    class Config:
        from_attributes = True
        populate_by_name = True
        arbitrary_types_allowed = True

class ReadScenario(BaseModel):
    id: int 
    name: str
    description: Optional[str] 

    class Config:
        from_attributes = True
        populate_by_name = True
        arbitrary_types_allowed = True

class CreateScenario(BaseModel):
    name: str
    description: Optional[str] 

    class Config:
        from_attributes = True
        populate_by_name = True
        arbitrary_types_allowed = True

class Plant(BaseModel):
    id: int
    name: str
    description: str
    address: str
    plantConfidence: float 
    zones : list[ReadZone] = []
    plantstatus: PlantStatusEnum

    class Config:
        from_attributes = True
        populate_by_name = True
        arbitrary_types_allowed = True

class ReadPlant(BaseModel):
    id: int
    name: str
    description: str
    address: str
    plantConfidence: float
    #zones : Optional[list[ReadZone]]
    plantstatus: PlantStatusEnum 

    class Config:
        from_attributes = True
        populate_by_name = True
        arbitrary_types_allowed = True

class CreatePlant(BaseModel):
    name: str
    description: str
    address: str
    plantConfidence: float

    class Config:
        from_attributes = True
        populate_by_name = True
        arbitrary_types_allowed = True

class UpdatePlant(BaseModel):
    plantConfidence: float

    class Config:
        from_attributes = True
        populate_by_name = True
        arbitrary_types_allowed = True

class ReadAssignee(BaseModel):
    id: int
    name: str
    email: str
    phone: str

    class Config:
        from_attributes = True
        populate_by_name = True
        arbitrary_types_allowed = True

class CreateAssignee(BaseModel):
    name: str
    email: str
    phone: str

    class Config:
        from_attributes = True
        populate_by_name = True
        arbitrary_types_allowed = True

class ReadDetectionType(BaseModel):
    id: int 
    name: str
    description: str 

    class Config:
        from_attributes = True
        populate_by_name = True
        arbitrary_types_allowed = True

class CreateInstance(BaseModel):
    recording: CreateRecording
    scenarios: list[ReadScenario]

class ReadInstance(BaseModel):
    recording: ReadRecording
    scenarios: list[ReadScenario]

class IncidentTypeCount(BaseModel):
    type: str
    count: int

class IncidentTimeline(BaseModel):
    date: str
    counts: Dict[str, int] 

class CombinedIncidentData(BaseModel):
    incidents_by_type: list[IncidentTypeCount]
    incident_timeline: list[IncidentTimeline]