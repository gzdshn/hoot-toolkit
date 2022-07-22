import dataclasses
from typing import List
import datetime

@dataclasses.dataclass
class AnnotatedFrameSet:
    '''Represents a video broken down into frames along with annotation-data and metadata'''
    id: int
    url: str
    sha256: str
    download_size: int   #bytes (64-bit minimum)
    install_size: int    #bytes (64-bit minimum)
    labels: List[str]=dataclasses.field(default_factory=list)

@dataclasses.dataclass
class TargetClass:
    '''Represents a set of videos featuring a single type of tracked object (eg: banana, keyboard, animal)'''
    name: str
    videos: List[AnnotatedFrameSet]=dataclasses.field(default_factory=list)

@dataclasses.dataclass
class HootDataset:
    version: str
    change_log: str
    date_created: datetime.date=dataclasses.field(default_factory=lambda: datetime.date.today())
    classes: List[TargetClass]=dataclasses.field(default_factory=list)
